
"""define the transportation engine for upload the data.

"""
import time
import logging
import socket
from tingyun.config.settings import global_settings, merge_settings, get_upload_settings
from tingyun.logistics.exceptions import RetryDataForRequest
from tingyun.packages import requests
from tingyun.logistics.transportation import transmitter

console = logging.getLogger(__name__)


class Engine(object):
    """this class hold the application session information from headquarters
    """
    def __init__(self, url, config, license_key, redirect_host):
        self.url = url
        self.config = config
        self.license_key = license_key
        self.local_setting = global_settings()
        self.merged_settings = config
        self.redirect_host = redirect_host

        self._session = None
        self.request_param = {
            "licenseKey": self.license_key,
            "version": self.local_setting.data_version,
            "appSessionKey": self.config.appSessionKey,
        }

    @property
    def session(self):
        """
        :return:
        """
        if self._session is None:
            self._session = requests.session()

        return self._session

    def close_session(self):
        """use to shutdown session, report status to server for test.
        """
        self._session.close()
        self._session = None

    def send_performance_metric(self, metric_data):
        """
        """
        return transmitter(self.session, self.url, "send_collect_data", metric_data, self.request_param,
                           self.config.audit_mode)

    def send_error_trace(self, error_trace):
        """
        """
        if not error_trace:
            return

        return transmitter(self.session, self.url, "send_error_trace", error_trace, self.request_param,
                           self.config.audit_mode)

    def send_action_trace(self, action_trace):
        """
        """
        if not action_trace:
            return

        return transmitter(self.session, self.url, "send_action_trace", action_trace, self.request_param,
                           self.config.audit_mode)

    def send_sql_trace(self, sql_trace):
        """
        """
        if not sql_trace:
            return

        return transmitter(self.session, self.url, "send_sql_trace", sql_trace, self.request_param,
                           self.config.audit_mode)

    def send_profile_data(self, data):
        """it allow to send empty data.
        """
        audit_mode = self.config.audit_mode
        url = connect_url("uploadAgentCommands", self.redirect_host)
        if not data:
            return

        return transmitter(self.session, url, "send_profile_data", data, self.request_param, audit_mode)

    def request_agent_commands(self):
        """
        """
        url = connect_url("getAgentCommands", self.redirect_host)
        audit_mode = self.config.audit_mode
        result = transmitter(self.session, url, "get_agent_commands", {}, self.request_param, audit_mode)

        return result

    def send_external_error_trace(self, external_error_trace):
        """
        """
        if not external_error_trace:
            return

        return transmitter(self.session, self.url, "send_external_error_trace", external_error_trace,
                           self.request_param, self.config.audit_mode)


def connect_url(action, host=None, with_port=False):
    """
    :param action: the uploader actually intention
    :return: ruled url, the suitable url according to headquarters strategy
    """
    settings = global_settings()
    scheme = settings.ssl and 'https' or 'http'
    url_reg = "%s://%s/%s"

    if host is None:
        host = settings.host

    url = url_reg % (scheme, host, action)
    if with_port and settings.port:
        url_reg = "%s://%s:%s/%s"
        url = url_reg % (scheme, host, settings.port, action)

    return url


def create_connection(license_key, app_name, linked_applications, machine_env, settings):
    """
    :return:
    """
    start_time = time.time()

    if not license_key:
        license_key = settings.license_key

    if not license_key:
        console.error("license key should be provided in tingyun.ini config file, agent may can not started.")

    try:
        console.info("init app with license: %s, app: %s, link app: %s, env: %s, settings: %s, upload settings: %s",
                     license_key, app_name, linked_applications, machine_env, settings, get_upload_settings())

        # when private the agent. we should get redirect with port set in settings
        url = connect_url("getRedirectHost", with_port=True)
        param = {"licenseKey": license_key, "version": settings.data_version}
        redirect_host = transmitter(None, url, "getRedirectHost", {}, param)
        local_conf = {
            "host": socket.gethostname(),
            "appName": [app_name] + linked_applications,
            "language": "Python",
            "agentVersion": settings.agent_version,
            "config": get_upload_settings(),
            "env": machine_env
        }

        # At second step. we need not the port with url. because the returned redirect url take it or has default 80.
        url = connect_url("initAgentApp", redirect_host, with_port=False)
        server_conf = transmitter(None, url, "initAgentApp", local_conf, {"licenseKey": license_key})
        app_config = merge_settings(server_conf)
    except Exception as err:
        console.error("errors when connect to server %s", err)
        raise RetryDataForRequest("Errors occurred, when create session with server. %s" % err)
    else:
        console.info("Successful register application to agent server with name: %s, use time: %ss", app_name,
                     time.time() - start_time)

        url = connect_url("upload", redirect_host)
        return Engine(url, app_config, license_key, redirect_host)
