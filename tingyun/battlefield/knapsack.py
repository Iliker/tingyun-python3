
import logging
import os
import sys
import threading
import weakref
import _thread


console = logging.getLogger(__name__)


class Knapsack(object):
    """
    """
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._cache = weakref.WeakValueDictionary()
        console.debug("init tracker with thread %s", thread.get_ident())

    @staticmethod
    def singleton_instance():
        """
        :return: singleton instance
        """
        if Knapsack._instance:
            return Knapsack._instance

        instance = None
        with Knapsack._instance_lock:
            if not Knapsack._instance:
                instance = Knapsack()
                Knapsack._instance = instance

                console.info('Creating instance of tracker Knapsack in  process %d.', os.getpid())

        return instance

    def current_thread_id(self):
        """get the current thread id
        :return: thread id
        """
        greenlet = sys.modules.get('greenlet')

        if greenlet:
            # Compatible greenlet frame
            current = greenlet.getcurrent()
            if current is not None and current.parent:
                return id(current)

        return thread.get_ident()

    def save_tracker(self, tracker):
        """
        :param tracker:
        :return:
        """
        if tracker.thread_id in self._cache:
            raise RuntimeError("tracker already exist.")

        self._cache[tracker.thread_id] = tracker

    def get_active_threads(self):
        """
        """
        for thread_id, frame in sys._current_frames().items():
            tracker = self._cache.get(thread_id)
            if tracker is not None:
                if tracker.background_task:
                    yield tracker, thread_id, 'Background', frame
                else:
                    yield tracker, thread_id, 'Web', frame
            else:
                active_thread = threading._active.get(thread_id)
                if active_thread is not None and active_thread.getName().startswith('TingYun-'):
                    yield None, thread_id, 'Agent', frame
                else:
                    yield None, thread_id, 'Other', frame

    def drop_tracker(self, tracker):
        """
        """
        thread_id = tracker.thread_id

        if thread_id not in self._cache:
            RuntimeError('no active tracker')

        current = self._cache.get(thread_id, None)
        if tracker != current:
            raise RuntimeError('not the current tracker')

        del self._cache[thread_id]

    def current_tracker(self):
        """Return the tracker object if one exists for the currently executing thread.
        """
        thread_id = self.current_thread_id()
        
        return self._cache.get(thread_id, None)

_knapsack = Knapsack()


def knapsack():
    """
    """
    return _knapsack
