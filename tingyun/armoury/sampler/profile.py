""" define this module for do the thread profile analyze

"""
import threading
import logging
import time

try:
    from sys import intern
except ImportError:
    pass

from tingyun.config.settings import global_settings
from tingyun.battlefield.knapsack import knapsack

console = logging.getLogger(__name__)
RUNNABLE_STATUS_FUNC = ['wait', 'sleep']


class ProfileTraceNode(object):
    """
    """
    def __init__(self, category="", class_name="", method_name="", line_num=0, is_runnable=None):
        """
        """
        self.runnable = 0
        self.non_runnable = 0
        self.class_name = class_name
        self.method_name = method_name
        self.line_num = line_num
        self.category = category
        self.depth = 0
        self.retrieve_depth = 0

        self.children = {}  # {func_name: node}
        self.is_runnable = is_runnable  # {"is_runnable": False} just for profile data node loop used to mark.

    @property
    def trace_segment(self):
        """
        """
        return [self.class_name, self.method_name, self.line_num]

    def has_child(self):
        """
        """
        if len(self.children) > 0:
            return True

        return False

    def format_data(self):
        """ just return the basic data, not include child node
        """
        return [self.trace_segment, self.runnable, self.non_runnable]

    def append_child(self, key, child):
        """
        """
        self.children[key] = child

    def get_child_key(self):
        """ a new trace node should has one child at most.
        """
        if not self.has_child():
            return 'unknown'

        return self.children.keys()[0]


class Profile(object):
    """
    """

    def __init__(self, profile_id):
        """
        """
        self.profile_id = profile_id
        self.start_time = int(time.time() * 1000)
        self.end_time = 0
        self.final_data = {"Web": {"cpuTime": 0, "threadTraces": []}, "Background": {"cpuTime": 0, "threadTraces": []},
                           "Agent": {"cpuTime": 0, "threadTraces": []}, "Other": {"cpuTime": 0, "threadTraces": []}}
        self.sample_count = 0
        self.thread_count = 0
        self.total_runnable_count = 0
        self.stacktraces = {}
        self.max_retrieve_depth = global_settings().max_profile_depth  # avoid reaching python max recursion depth.
        self.retrieve_depth = 0

    def profile_data(self):
        """Note, we do not update the root node basic data.(runnable,non-runnable)
        The root node dose not include the thread data.

        """
        for category in self.final_data:

            if (category not in self.stacktraces) or (not self.stacktraces[category].has_child()):
                console.info("Get empty data with category: %s", category)
                self.final_data[category]['threadTraces'] = []
                continue

            # retrieve_profile_node() will lost the first node of the profile. so rebuild default one
            # if node in self.stacktraces
            root = [['-', 'PythonProfileEntryFunc', 1], 1, 1, []]
            self.retrieve_profile_node(self.stacktraces[category], root)
            self.final_data[category]['threadTraces'] = root[3]

        payload = {"profileId": self.profile_id, "beginTime": self.start_time, "endTime": self.end_time,
                   "sampleCount": self.sample_count, "threads": self.thread_count,
                   "stacktraces": str(self.final_data), "runnableThreads": self.total_runnable_count}
        return payload

    def retrieve_profile_node(self, profile_node, parent):
        """
        :param profile_node:
        :return:
        """
        self.retrieve_depth += 1

        if not profile_node.has_child() or profile_node.retrieve_depth > self.max_retrieve_depth:
            parent[3].append(profile_node.format_data() + [[]])
            return

        for key in profile_node.children:
            node = profile_node.children[key]

            data_node = node.format_data() + [[]]
            parent[3].append(data_node)

            self.retrieve_profile_node(node, data_node)

    def update_thread_trace(self, category, new_node):
        """
        :param category:
        :param new_node: new stack trace node
        :return:
        """
        if category != new_node.category:
            return

        # very important. node with head node without data maybe cause data lost.
        if not new_node.has_child:
            console.info("New profile node is empty, ignore it now.")
            return

        key = category
        if key not in self.stacktraces:
            self.update_trace_node_runnable_status(new_node)
            self.stacktraces[key] = new_node
            # console.info('new tree with category: %s, data: %s', category, new_node)
            return

        # it's dict
        root_tree = self.stacktraces[key]

        while True:
            # only one child exist if new node has child. this will drop the first node.
            if not new_node.has_child():
                break

            # note: the top level node of the new node is a empty node.
            # It's new branch of the root node. so break out
            # root_tree can not use the append_child method, because the current node is lost just get the child(dict)
            child_key = new_node.get_child_key()
            if child_key not in root_tree.children:
                self.update_trace_node_runnable_status(new_node.children[child_key])
                root_tree.children[child_key] = new_node.children[child_key]
                break

            # update the node attribution
            if new_node.is_runnable["is_runnable"]:
                root_tree.children[child_key].runnable += 1
            else:
                root_tree.children[child_key].non_runnable += 1

            # deal the child node.
            root_tree = root_tree.children[child_key]
            new_node = new_node.children[child_key]

    def update_trace_node_runnable_status(self, trace_node):
        """ the trace node must be single tree switch. it is used in new thread trace node
        :param trace_node:
        :return:
        """
        runnable = trace_node.is_runnable["is_runnable"]
        root = trace_node

        while root:
            if runnable:
                root.runnable = 1
            else:
                root.non_runnable = 1

            if root.has_child():
                root = root.children.values()[0]
            else:
                break


class ProfileManager(object):
    """Note: Now we are not support multi application. only use the profile id as verification.
    """
    lock = threading.Lock()
    instance = None

    def __init__(self):
        """we provide local setting switch, just used when exception occurred in user environment.
        enable parameter will be removed in the future.
        :return:
        """
        self.enable = global_settings().enable_profile
        self.current_profile = None

        self._profile_shutdown = threading.Event()
        self.profile_thread_running = False  # not running
        self.profile_thread = None
        self.cmd_info = {}
        self.finished_profiles = []
        self.cmd_stop_status = False
        self.generated_data = None

    @staticmethod
    def singleton():
        with ProfileManager.lock:
            if ProfileManager.instance is None:
                ProfileManager.instance = ProfileManager()

        return ProfileManager.instance

    def start_profile(self, cid, app_name, profile_id, duration, interval):
        """
        :param app_name:
        :param profile_id:
        :param duration: sample the profile duration, 'seconds' format
        :param interval: mile seconds format
        :return: True/False
        """
        self.cmd_info['cid'] = cid
        self.cmd_info['profile_id'] = profile_id
        self.cmd_info['duration'] = duration
        self.cmd_info['interval'] = interval / 1000.0
        self.cmd_info['app_name'] = app_name
        self.cmd_info['end_time'] = time.time() + duration

        if not self.enable:
            console.info("profile disabled in local settings.")
            return False

        if self.current_profile:
            console.warning("There's maybe running a profile, this is a unnormal status, if this continues,"
                            "please report us for further investigation.")
            return False

        with self.lock:
            if self.profile_thread_running:
                console.warning("There are running a thread profile, this is a unnormal status, if this continues,"
                                "please report us for further investigation.")
                return False

            self.current_profile = Profile(profile_id)

            self.profile_thread = threading.Thread(target=self._do_profile, name="TingYun-profile-thread")
            self.profile_thread.setDaemon(True)
            self.profile_thread.start()

            self.profile_thread_running = True  # running.

        return True

    def stop_profile(self):
        """
        :return:
        """
        with self.lock:
            if self.current_profile:
                self.current_profile.end_time = int(time.time() * 1000)
                self.finished_profiles.append(self.current_profile)

            self.current_profile = None
            self.profile_thread_running = False

    def _do_profile(self):
        """
        :return:
        """
        console.info("Staring thread for doing profile.")
        while True:
            if not self.current_profile:
                console.info("Stopping profile now.")
                return

            self.current_profile.sample_count += 1
            for thread_id, category, stack_node in self.trace_thread_stack():
                if not stack_node.has_child():
                    console.debug("Do not get the thread stacktrace.")
                    continue

                self.current_profile.update_thread_trace(category, stack_node)

            self.update_profile_status()

            interval = 0.1 if not self.cmd_info["interval"] else self.cmd_info["interval"]
            self._profile_shutdown.wait(interval)

    def update_profile_status(self):
        """
        :return:
        """
        if self.current_profile:
            if time.time() > self.cmd_info['end_time']:
                self.stop_profile()
                console.info("Finish the profile thread.")

    def trace_thread_stack(self):
        """
        :return:
        """
        for tracker, thread_id, category, frame in knapsack().get_active_threads():
            # top level node for profile
            is_runnable = {"is_runnable": True}
            top_node = ProfileTraceNode(category, "-", 'PythonProfileEntryFunc', 0, is_runnable)
            father = top_node
            self.current_profile.thread_count += 1
            while frame:
                code = frame.f_code
                child = ProfileTraceNode(category, intern(code.co_filename), intern(code.co_name), frame.f_lineno,
                                         is_runnable)
                father.append_child(intern(code.co_name), child)
                father = child
                top_node.depth += 1
                frame = frame.f_back

                # mark it is runnable thread or not
                if intern(intern(code.co_name)) in RUNNABLE_STATUS_FUNC:
                    is_runnable['is_runnable'] = False
                    break

            if is_runnable['is_runnable']:
                self.current_profile.total_runnable_count += 1

            yield thread_id, category, top_node

    def generate_profile_data(self):
        """
        :return:
        """
        if not self.enable:
            profile = Profile(self.cmd_info['profile_id'])
            self.finished_profiles.append(profile)

        # dose not finished
        if self.current_profile:
            return None

        # server stop command
        if self.cmd_stop_status:
            return None

        if 0 == len(self.finished_profiles):
            console.warning("We got empty profile data, this maybe some issues of the python code, if this continues, "
                            "please report to us ofr further investigation. Thank U.")
            console.warning("Current command information is %s", self.cmd_info)
            return None

        try:
            final_data = {"id": self.cmd_info['cid'], "result": self.finished_profiles[0].profile_data()}
        except Exception as err:
            console.warning("Errors, when generate profile data. %s, %s", self.cmd_info, err)
            self.finished_profiles = []
            return None

        self.finished_profiles = []

        return final_data

    def shutdown(self, stop_cmd=False):
        """
        :return:
        """
        console.info("Force shutdown the profile, because receive the shutdown signals.")
        self.stop_profile()
        self.finished_profiles = []
        if stop_cmd:
            self.cmd_stop_status = True

        return True


def get_profile_manger():
    """only singleton mode used.
    :return:
    """
    return ProfileManager.singleton()
