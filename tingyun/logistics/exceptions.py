import logging

""" define some exception class for internal usage
"""

console = logging.getLogger(__name__)


class ConfigurationError(Exception):
    pass


class NetworkInterfaceException(Exception):
    pass


class ForceAgentRestart(NetworkInterfaceException):
    pass


class ForceAgentDisconnect(NetworkInterfaceException):
    pass


class DiscardDataForRequest(NetworkInterfaceException):
    pass


class RetryDataForRequest(NetworkInterfaceException):
    pass


class ServerIsUnavailable(RetryDataForRequest):
    pass


class InvalidLicenseException(NetworkInterfaceException):
    pass


class InvalidDataTokenException(NetworkInterfaceException):
    pass


class OutOfDateConfigException(NetworkInterfaceException):
    pass


class CommandlineParametersException(Exception):
    pass