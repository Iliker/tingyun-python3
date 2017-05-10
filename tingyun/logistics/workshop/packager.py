# -*- coding:utf-8 -*-

"""this module is implement to deal the tracker all data
"""

import copy

import logging
import threading
from tingyun.logistics.workshop.quantile import QuantileP2
from tingyun.logistics.workshop.packets import TimePackets, ApdexPackets, SlowSqlPackets
from tingyun.packages import six


console = logging.getLogger(__name__)


class Packager(object):
    """
    """
    def __init__(self):
        self.__max_error_count = 20
        self.__settings = None

        self.__time_packets = {}  # store time packets data key is name + scope
        self.__apdex_packets = {}
        self.__action_packets = {}
        self.__general_packets = {}
        # it's maybe include {name: {trackerType, count, $ERROR_ITEM}}
        # $ERROR_ITEM  detail, check the documentation
        self.__traced_errors = {}

        # it's maybe include {name: {count, $ERROR_ITEM}}
        # $ERROR_ITEM  detail, check the documentation
        self.__traced_external_errors = {}

        # format: {$"metric_name": [$slow_action_data, $duration]}
        self.__slow_action = {}
        self.__slow_sql_packets = {}

        # quantile
        self.__quantile_data = None
        self.__quantile = {}

        self._packets_lock = threading.Lock()

    @property
    def settings(self):
        """
        :return:
        """
        return self.__settings

    def create_data_zone(self):
        """create empty data engine to contain the unmerged tracker data
        :return:
        """
        zone = Packager()
        zone.__settings = self.__settings

        return zone

    def reset_packets(self, application_settings):
        """
        :param application_settings: application settings from server and setting file
        :return:
        """
        self.__settings = application_settings

        self.__time_packets = {}
        self.__apdex_packets = {}
        self.__action_packets = {}
        self.__general_packets = {}
        self.__traced_errors = {}
        self.__traced_external_errors = {}
        self.__slow_action = {}
        self.__slow_sql_packets = {}

    def record_tracker(self, tracker):
        """
        :param tracker: tracker node instance
        :return:
        """
        if not self.__settings:
            console.error("The application settings is not merge into data engine.")
            return

        node_limit = self.__settings.action_tracer_nodes
        threshold = self.__settings.action_tracer.action_threshold

        self.record_time_metrics(tracker.time_metrics())  # deal for component, include framework/db/other
        self.record_quantile(*tracker.quantile())
        self.record_action_metrics(tracker.action_metrics())  # deal for user action
        self.record_apdex_metrics(tracker.apdex_metrics())  # for recording the apdex
        self.record_traced_errors(tracker.traced_error())  # for error trace detail
        self.record_slow_action(tracker.slow_action_trace(node_limit, threshold))
        self.record_slow_sql(tracker.slow_sql_nodes())
        self.record_traced_external_trace(tracker.traced_external_error())

    def record_quantile(self, action, duration):
        """
        :return:
        """
        if 0 == len(self.__settings.quantile):
            return

        self.__quantile_data = (action, duration)

    def record_slow_sql(self, nodes):
        """
        :param nodes: the slow sql node
        :return:
        """
        if not self.__settings.action_tracer.slow_sql:
            return

        for node in nodes:
            if len(self.__slow_sql_packets) > self.__settings.slow_sql_count:
                console.debug("Slow sql count is more than max count %s", self.__settings.slow_sql_count)
                continue

            key = node.request_uri + node.sql
            packets = self.__slow_sql_packets.get(key)
            if not packets:
                packets = SlowSqlPackets()

            packets.merge_slow_sql_node(node)
            self.__slow_sql_packets[key] = packets

    def record_slow_action(self, slow_action):
        """
        :param slow_action:
        :return:
        """
        if not self.__settings.action_tracer.enabled:
            return

        # 不能在这里通过判断阈值是否到达临界去除法慢过程，因为可能因为跨应用而强制触发
        # 如果节点返回`无效数据`则直接丢弃
        if not slow_action:
            return

        top_n = self.__settings.action_tracer.top_n
        metric_name = slow_action[2]

        if metric_name not in self.__slow_action:
            self.__slow_action[metric_name] = [[slow_action, slow_action[1]]]
        else:
            # every request url/metric can save top_n action trace.
            if len(self.__slow_action[metric_name]) <= top_n:
                self.__slow_action[metric_name].append([slow_action, slow_action[1]])

    def record_traced_errors(self, traced_errors):
        """
        :return:
        """
        if not self.__settings.error_collector.enabled:
            return

        for error in traced_errors:
            if len(self.__traced_errors) > self.__max_error_count:
                console.debug("Error trace is reached maximum limitation.")
                break

            if error.error_filter_key in self.__traced_errors:
                self.__traced_errors[error.error_filter_key]["count"] += 1
                self.__traced_errors[error.error_filter_key]["item"][-3] += 1
            else:
                self.__traced_errors[error.error_filter_key] = {"count": 1,
                                                                "item": error.trace_data,
                                                                "tracker_type": error.tracker_type}

    def record_traced_external_trace(self, traced_errors):
        """
        :param traced_errors:
        :return:
        """
        if not self.__settings.error_collector.enabled:
            return

        for error in traced_errors:
            if len(self.__traced_external_errors) > self.__max_error_count:
                console.debug("External error trace is reached maximum limitation.")
                break

            if error.error_filter_key in self.__traced_external_errors:
                self.__traced_external_errors[error.error_filter_key]["count"] += 1
                self.__traced_external_errors[error.error_filter_key]["item"][-3] += 1

            else:
                self.__traced_external_errors[error.error_filter_key] = {"count": 1, "status_code": error.status_code,
                                                                         "item": error.trace_data,
                                                                         "tracker_type": error.tracker_type}

    def record_general_metric(self, metric):
        """
        :param metric:
        :return:
        """
        key = (metric.name.split("/", 1)[1], '')

        packets = self.__general_packets.get(key)
        if packets is None:
            packets = TimePackets()

        packets.merge_time_metric(metric)
        self.__general_packets[key] = packets

        return key

    def record_time_metric(self, metric):
        """
        :param metric:
        :return:
        """
        # filter the general data from the metric, the metric node should be distinguish general and basic metric
        if metric.name.startswith("GENERAL"):
            self.record_general_metric(metric)
            return

        key = (metric.name, metric.scope or '')  # metric key for protocol
        packets = self.__time_packets.get(key)
        if packets is None:
            packets = TimePackets()

        packets.merge_time_metric(metric)
        self.__time_packets[key] = packets

        return key

    def record_time_metrics(self, metrics):
        """
        :param metrics:
        :return:
        """
        for metric in metrics:
            self.record_time_metric(metric)

    def record_apdex_metric(self, metric):
        """
        :param metric:
        :return:
        """
        key = (metric.name, "")
        packets = self.__apdex_packets.get(key)

        if packets is None:
            packets = ApdexPackets(apdex_t=metric.apdex_t)

        packets.merge_apdex_metric(metric)
        self.__apdex_packets[key] = packets
        return key

    def record_apdex_metrics(self, metrics):
        """
        :param metrics:
        :return:
        """
        for metric in metrics:
            self.record_apdex_metric(metric)

    def record_action_metric(self, metric):
        """
        :param metric:
        :return:
        """
        key = (metric.name, metric.scope or '')  # metric key for protocol
        packets = self.__action_packets.get(key)
        if packets is None:
            packets = TimePackets()

        packets.merge_time_metric(metric)
        self.__action_packets[key] = packets

        return key

    def record_action_metrics(self, metrics):
        """
        :param metrics:
        :return:
        """
        for metric in metrics:
            self.record_action_metric(metric)

    def rollback(self, stat, merge_performance=True):
        """rollback the performance data when upload the data failed. except the traced error count.
        :param stat:
        :param merge_performance:
        :return:
        """
        if not merge_performance:
            return

        console.warning("Agent will rollback the data which is captured at last time. That indicates your network is"
                        " broken.")

        for key, value in six.iteritems(stat.__time_packets):
            packets = self.__time_packets.get(key)
            if not packets:
                self.__time_packets[key] = copy.copy(value)
            else:
                packets.merge_packets(value)

        for key, value in six.iteritems(stat.__apdex_packets):
            packets = self.__apdex_packets.get(key)
            if not packets:
                self.__apdex_packets[key] = copy.copy(value)
            else:
                packets.merge_packets(value)

        for key, value in six.iteritems(stat.__action_packets):
            packets = self.__action_packets.get(key)
            if not packets:
                self.__action_packets[key] = copy.copy(value)
            else:
                packets.merge_packets(value)

        for key, value in six.iteritems(stat.__general_packets):
            packets = self.__general_packets.get(key)
            if not packets:
                self.__general_packets[key] = copy.copy(value)
            else:
                packets.merge_packets(value)

        for key, value in six.iteritems(stat.__traced_errors):
            packets = self.__traced_errors.get(key)
            if not packets:
                self.__traced_errors[key] = copy.copy(value)
            else:
                packets["count"] += value["count"]

        for key, value in six.iteritems(stat.__traced_external_errors):
            packets = self.__traced_external_errors.get(key)
            if not packets:
                self.__traced_external_errors[key] = copy.copy(value)
            else:
                packets["count"] += value["count"]

    def merge_metric_packets(self, snapshot):
        """
        :param snapshot:
        :return:
        """
        for key, value in six.iteritems(snapshot.__time_packets):
            packets = self.__time_packets.get(key)
            if not packets:
                self.__time_packets[key] = copy.copy(value)
            else:
                packets.merge_packets(value)

        for key, value in six.iteritems(snapshot.__apdex_packets):
            packets = self.__apdex_packets.get(key)
            if not packets:
                self.__apdex_packets[key] = copy.copy(value)
            else:
                packets.merge_packets(value)

        for key, value in six.iteritems(snapshot.__action_packets):
            packets = self.__action_packets.get(key)
            if not packets:
                self.__action_packets[key] = copy.copy(value)
            else:
                packets.merge_packets(value)

        # TODO: think more about the background task
        for key, value in six.iteritems(snapshot.__traced_errors):
            packets = self.__traced_errors.get(key)
            if not packets:
                self.__traced_errors[key] = copy.copy(value)
            else:
                packets["item"][-3] += value["count"]

        for key, value in six.iteritems(snapshot.__traced_external_errors):
            packets = self.__traced_external_errors.get(key)
            if not packets:
                self.__traced_external_errors[key] = copy.copy(value)
            else:
                packets["item"][-3] += value["count"]

        # generate general data
        for key, value in six.iteritems(snapshot.__general_packets):
            packets = self.__general_packets.get(key)
            if not packets:
                self.__general_packets[key] = copy.copy(value)
            else:
                packets.merge_packets(value)

        # for action trace
        top_n = self.__settings.action_tracer.top_n
        for key, value in six.iteritems(snapshot.__slow_action):

            if key not in self.__slow_action:
                self.__slow_action[key] = value
                break

            slow_actons = self.__slow_action.get(key)
            # although the target action trace value is `list`, but it only has 1 element in one metric.
            if len(slow_actons) > top_n:
                console.debug("The action trace is reach the top(%s), action(%s) is ignored.", top_n, key)
                break
            slow_actons.extend(value)

        # for slow sql
        max_sql = self.__settings.slow_sql_count
        for key, value in six.iteritems(snapshot.__slow_sql_packets):
            if len(self.__slow_sql_packets) > max_sql:
                console.debug("The slow sql trace count is reach the top.")
                continue

            slow_sql = self.__slow_sql_packets.get(key)
            if not slow_sql:
                self.__slow_sql_packets[key] = value
            else:
                slow_sql.merge_packets(value)

        # for quantile
        if 0 != len(self.__settings.quantile):
            action, duration = snapshot.__quantile_data
            if action not in self.__quantile:
                self.__quantile[action] = QuantileP2(self.__settings.quantile)

            self.__quantile[action].add(duration)

    def reset_metric_packets(self):
        """
        :return:
        """
        self.__time_packets = {}  # component
        self.__apdex_packets = {}
        self.__action_packets = {}
        self.__general_packets = {}

        self.__traced_errors = {}
        self.__traced_external_errors = {}
        self.__slow_action = {}
        self.__slow_sql_packets = {}

        self.__quantile = {}

    def packets_snapshot(self):
        """
        :return:
        """
        stat = copy.copy(self)

        self.__time_packets = {}
        self.__action_packets = {}
        self.__apdex_packets = {}
        self.__traced_errors = {}
        self.__traced_external_errors = {}
        self.__general_packets = {}
        self.__slow_action = {}
        self.__slow_sql_packets = {}
        self.__quantile = {}

        return stat

    # just for upload performance package
    # strip to 5 parts
    def component_metrics(self, metric_name_ids):
        """
        :return:
        """
        result = []

        for key, value in six.iteritems(self.__time_packets):
            extend_metrics = key[0].split("|")
            if len(extend_metrics) == 1:
                upload_key = {"name": key[0], "parent": key[1]}
                upload_key_str = '%s:%s' % (key[0], key[1])
                upload_key = upload_key if upload_key_str not in metric_name_ids else metric_name_ids[upload_key_str]
                result.append([upload_key, value])
            elif len(extend_metrics) == 3:
                upload_key = {"name": extend_metrics[0], "parent": key[1], "calleeId": extend_metrics[1],
                              "calleeName": extend_metrics[2]}
                result.append([upload_key, value])

        self.__time_packets = {}
        return result

    def apdex_data(self, metric_name_ids):
        """
        :return:
        """
        result = []

        for key, value in six.iteritems(self.__apdex_packets):
            upload_key = {"name": key[0]}
            upload_key_str = '%s' % key[0]
            upload_key = upload_key if upload_key_str not in metric_name_ids else metric_name_ids[upload_key_str]
            result.append([upload_key, value])

        # reset the data if returned for upload.
        self.__apdex_packets = {}
        return result

    def action_metrics(self, metric_name_ids):
        """
        :return:
        """
        result = []
        for key, value in six.iteritems(self.__action_packets):
            upload_key = {"name": key[0]}
            upload_key_str = '%s' % key[0]
            upload_key = upload_key if upload_key_str not in metric_name_ids else metric_name_ids[upload_key_str]

            if 0 != len(self.__settings.quantile):
                result.append([upload_key, value, self.__quantile[upload_key_str].markers])
            else:
                result.append([upload_key, value])

        # reset the data if returned for upload.
        self.__action_packets = {}
        return result

    def error_packets(self, metric_name_ids):
        """stat the error trace metric for performance
        :return:
        """
        external_error, web_action_error = 'External', 'WebAction'
        error_types = [external_error, web_action_error]
        error_count = {
            "Errors/Count/All": 0,
            "Errors/Count/AllWeb": 0,
            "Errors/Count/AllBackground": 0
        }

        def parse_error_trace(traced_data):
            for error_filter_key, error in six.iteritems(traced_data):
                error_count["Errors/Count/All"] += error["count"]

                if error["tracker_type"] in error_types:
                    error_count["Errors/Count/AllWeb"] += error["count"]

                    action_key = "Errors/Count/%s" % error_filter_key.split("_|")[0]
                    if action_key not in error_count:
                        error_count[action_key] = error["count"]
                    else:
                        error_count[action_key] += error["count"]

                    if error["tracker_type"] == external_error:
                        action_key = "Errors/Type:%s/%s" % (error["status_code"], error_filter_key.split("_|")[0])
                        if action_key not in error_count:
                            error_count[action_key] = error["count"]
                        else:
                            error_count[action_key] += error["count"]
                else:
                    error_count["Errors/Count/AllBackground"] += 1

        parse_error_trace(self.__traced_errors)
        parse_error_trace(self.__traced_external_errors)

        stat_value = []
        for key, value in six.iteritems(error_count):
            upload_key = {"name": key}
            upload_key_str = '%s' % key
            upload_key = upload_key if upload_key_str not in metric_name_ids else metric_name_ids[upload_key_str]
            stat_value.append([upload_key, [value]])

        return stat_value

    # stat for error trace data
    # rely to the basic error trace data structure
    def error_trace_data(self):
        """
        :return:
        """
        rtv = [error["item"] for error in six.itervalues(self.__traced_errors)]
        self.__traced_errors = {}

        return rtv

    def external_error_data(self):
        rtv = [error["item"] for error in six.itervalues(self.__traced_external_errors)]
        self.__traced_external_errors = {}

        return rtv

    def general_trace_metric(self, metric_name_ids):
        """
        :return:
        """
        result = []
        for key, value in six.iteritems(self.__general_packets):
            extend_keys = key[0].split("|")
            if len(extend_keys) == 1:
                upload_key = {"name": key[0]}
                upload_key_str = '%s' % key[0]
                upload_key = upload_key if upload_key_str not in metric_name_ids else metric_name_ids[upload_key_str]
                result.append([upload_key, value])
            elif len(extend_keys) == 3:
                # do not replace the metric with id.
                upload_key = {"name": extend_keys[0], "calleeId": extend_keys[1], "calleeName": extend_keys[2]}
                result.append([upload_key, value])

        self.__general_packets = {}
        return result

    def action_trace_data(self):
        """
        :return:
        """
        if not self.__slow_action:
            return []

        trace_data = []

        for traces in six.itervalues(self.__slow_action):
            for trace in traces:
                trace_data.append(trace[0])

        return {"type": "actionTraceData", "actionTraces": trace_data}

    def slow_sql_data(self):
        """
        :return:
        """
        if not self.__slow_sql_packets:
            return []

        result = {"type": "sqlTraceData", "sqlTraces": []}
        maximum = self.__settings.slow_sql_count
        slow_sql_nodes = sorted(six.itervalues(self.__slow_sql_packets), key=lambda x: x.max_call_time)[-maximum:]

        for node in slow_sql_nodes:
            explain_plan = node.slow_sql_node.explain_plan
            params = {"explainPlan": explain_plan if explain_plan else {}, "stacktrace": []}

            if node.slow_sql_node.stack_trace:
                for line in node.slow_sql_node.stack_trace:
                    line = [line.filename, line.lineno, line.name, line.locals]
                    if len(line) >= 4 and 'tingyun' not in line[0]:
                        params['stacktrace'].append("%s(%s:%s)" % (line[2], line[0], line[1]))

            result['sqlTraces'].append([node.slow_sql_node.start_time, node.slow_sql_node.path,
                                        node.slow_sql_node.metric, node.slow_sql_node.request_uri,
                                        node.slow_sql_node.formatted, node.call_count,
                                        node.total_call_time, node.max_call_time,
                                        node.min_call_time, str(params)])

        self.__slow_sql_packets = {}
        return result
