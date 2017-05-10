from collections import namedtuple


_ErrorNode = namedtuple('_ErrorNode', ['error_time', 'http_status', "error_class_name", 'uri', 'thread_name',
                                       "message", 'stack_trace', 'request_params', "tracker_type", "referer"])

_ExternalNode = namedtuple('_ExternalNode', ['error_time', 'status_code', 'url', 'thread_name', 'tracker_type',
                                             'error_class_name', 'stack_trace', 'request_params', 'http_status',
                                             'module_name'])


class ErrorNode(_ErrorNode):
    """

    """
    pass


class ExternalErrorNode(_ExternalNode):
    """
    """
    pass
