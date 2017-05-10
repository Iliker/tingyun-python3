"""this module implement data packets for packager

"""
import operator


class TimePackets(list):
    """six element of list
    """
    def __init__(self, call_count=0, total_call_time=0, total_exclusive_call_time=0, max_call_time=0,
                 min_call_time=0, sum_of_squares=0):
        super(TimePackets, self).__init__([call_count, total_call_time, total_exclusive_call_time, max_call_time,
                                           min_call_time, sum_of_squares])
    call_count = property(operator.itemgetter(0))
    total_call_time = property(operator.itemgetter(1))
    total_exclusive_call_time = property(operator.itemgetter(2))
    min_call_time = property(operator.itemgetter(4))
    max_call_time = property(operator.itemgetter(3))
    sum_of_squares = property(operator.itemgetter(5))

    def merge_packets(self, other):
        """Merge data from another instance of this object."""

        self[1] += other[1]
        self[2] += other[2]
        self[4] = self[0] and min(self[4], other[4]) or other[4]
        self[3] = max(self[3], other[3])
        self[5] += other[5]

        # Must update the call count last as update of the minimum call time is dependent on initial value.
        self[0] += other[0]

    def merge_original_time_metric(self, duration, exclusive=None):
        """Merge original time value."""

        if exclusive is None:
            exclusive = duration

        self[1] += duration
        self[2] += exclusive
        self[3] = max(self[3], duration)
        self[4] = self[0] and min(self[4], duration) or duration
        # self[3] = self[0] and min(self[3], duration) or duration
        # self[4] = max(self[4], duration)
        self[5] += duration ** 2

        # Must update the call count last as update of the minimum call time is dependent on initial value.
        self[0] += 1

    def merge_time_metric(self, metric):
        """Merge data from a time metric object."""
        self.merge_original_time_metric(int(metric.duration), int(metric.exclusive))


class ApdexPackets(list):
    """
    """
    def __init__(self, satisfying=0, tolerating=0, frustrating=0, apdex_t=0):
        super(ApdexPackets, self).__init__([satisfying, tolerating, frustrating, apdex_t])

    satisfying = property(operator.itemgetter(0))
    tolerating = property(operator.itemgetter(1))
    frustrating = property(operator.itemgetter(2))

    def merge_packets(self, other):
        """Merge data from another instance of this object."""

        self[0] += other[0]
        self[1] += other[1]
        self[2] += other[2]

    def merge_apdex_metric(self, metric):
        """Merge data from an apdex metric object."""

        self[0] += metric.satisfying
        self[1] += metric.tolerating
        self[2] += metric.frustrating


class SlowSqlPackets(list):

    def __init__(self):
        super(SlowSqlPackets, self).__init__([0, 0, 0, 0, None])

    call_count = property(operator.itemgetter(0))
    total_call_time = property(operator.itemgetter(1))
    min_call_time = property(operator.itemgetter(2))
    max_call_time = property(operator.itemgetter(3))
    slow_sql_node = property(operator.itemgetter(4))

    def merge_packets(self, other):
        """Merge data from another instance of this object."""

        self[1] += other[1]
        self[2] = self[0] and min(self[2], other[2]) or other[2]
        self[3] = max(self[3], other[3])

        if self[3] == other[3]:
            self[4] = other[4]

        # Must update the call count last as update of the minimum call time is dependent on initial value.
        self[0] += other[0]

    def merge_slow_sql_node(self, node):
        """Merge data from a slow sql node object."""

        duration = node.duration

        self[1] += duration
        self[2] = self[0] and min(self[2], duration) or duration
        self[3] = max(self[3], duration)

        if self[3] == duration:
            self[4] = node

        # Must update the call count last as update of the minimum call time is dependent on initial value.
        self[0] += 1
