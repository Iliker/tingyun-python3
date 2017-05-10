import copy
import logging
import os
import json
import re

from tingyun import get_version

console = logging.getLogger(__name__)
filter_pro = ["log_level_mapping", ]


class Settings(object):
    """
    """
    def __repr__(self):
        return repr(self.__dict__)

    def __iter__(self):
        """return the iteration for setting item
        """
        return iter(flatten_settings(self).items())


class ErrorCollectorSettings(Settings):
    pass


class ActionTracerSettings(Settings):
    pass


class Naming(Settings):
    """naming Rules class for use.
    """
    def __init__(self, rules=None):
        self.rules = json.loads(rules) if not isinstance(rules, list) else rules
        self.cached = {}  # {url:metric}
        self.regex_url = {}
        self.loaded = False
        self.method = {"0": "GET|POST|PUT|DELETE|HEAD", "1": "GET", "2": "POST", "3": "PUT", "4": "DELETE", "5": "HEAD"}
        self.match_type = {"1": self.match_equal, "2": self.match_start_with, "3": self.match_end_with,
                           "4": self.match_include, "5": self.match_regex, "0": self.any_value}

    @property
    def should_naming(self):
        return True if self.rules else False

    def any_value(self, src, dist, flag=0):
        return True

    def match_equal(self, src, dist, flag=0):
        """
        :param src: compare source data
        :param dist: compare target
        :return:
        """
        if isinstance(src, list):
            return dist in src

        return src == dist

    def match_start_with(self, src, dist, flag=0):
        if isinstance(src, list):
            for s in src:
                if str(s).startswith(dist):
                    return True
        else:
            return str(src).startswith(dist)

        return False

    def match_end_with(self, src, dist, flag=0):
        if isinstance(src, list):
            for s in src:
                if str(s).endswith(dist):
                    return True
        else:
            return str(src).endswith(dist)

        return False

    def match_include(self, src, dist, flag=0):
        if isinstance(src, list):
            for s in src:
                if str(dist) in str(s):
                    return True
        else:
            return str(dist) in str(src)

        return False

    def match_regex(self, src, dist, flag=re.IGNORECASE):

        if dist in self.regex_url:
            return self.regex_url.get(dist)

        def _match_value(_src, _dist, cache):
            for s in _src:
                pattern = re.compile(_dist, flag)
                match = pattern.match(s)

                if match:
                    cache[dist] = pattern
                    return True

            return False

        if isinstance(src, list):
            return _match_value(src, dist, self.regex_url)
        else:
            return _match_value([src], dist, self.regex_url)

    def naming_url_parameters(self, rule, params, grouped_param):
        """
        :param params:dict
        :param rule: rule
        :return:
        """
        if not rule:
            return ""
        p = "&".join(["%s=%s" % (k, params.get(k)) for k in rule.split(",") if k in params])
        grouped_param.append(p)
        return p

    def naming_web_action(self, method, uri, url_param, header_param, cookie_param):
        """ entrance for naming web action with rules
        :param cookie_param:
        :param url_param:
        :param header_param:
        :param method: current http request method to the Application
        :param uri: uri of current request
        :return:
        """
        if uri in self.cached:
            return self.cached.get(uri)

        if self.rules and not self.loaded:
            self.rules = json.loads(self.rules) if not isinstance(self.rules, list) else self.rules
            self.loaded = True

        if not self.rules:
            return None

        if not ("name" in self.rules[0] and "match" in self.rules[0] and "split" in self.rules[0]):
            self.rules = None
            return None

        for rule in self.rules:
            # match the request method
            if method not in self.method.get(str(rule["match"]["method"]), ""):
                continue

            # match the url rule, url case insensitive
            match_func = self.match_type[str(rule["match"]["match"])]
            if not match_func(uri, rule["match"]["value"], re.IGNORECASE):
                continue

            # match the parameters rule,not support body parameters, when match the value, the case sensitive
            # And the relationship between parameters and url matching is logic 'and'
            matched_param = True
            param_type = {"1": url_param, "2": header_param, "3": {}, "4": cookie_param}
            for params in rule["match"]['params']:
                assert isinstance(params, dict)

                src_value = param_type.get(str(params['type'])).get(params["name"], "")
                match_func = self.match_type[str(params["match"])]

                if not match_func(src_value, params["value"]):
                    matched_param = False
                    break

            # url match & param should be matched
            if not matched_param:
                continue

            named_metric = ["/", rule["name"], "/"]
            uri_rule = rule["split"]["uri"]
            if uri_rule:
                uri_section = uri.strip('/').split("/")
                uri_rules = [ur for ur in uri_rule.split(",") if ur]

                if 1 == len(uri_rules) and 0 < int(uri_rules[0]):
                    named_metric.append("/".join(uri_section[: int(uri_rules[0])]))
                elif 1 == len(uri_rules) and 0 > int(uri_rules[0]):
                    named_metric.append("/".join(uri_section[int(uri_rules[0]):]))
                elif len(uri_rules) > 1:
                    tmp = [uri_section[int(ux) - 1] for ux in uri_rules if int(ux) <= len(uri_section)]
                    named_metric.append("/".join(tmp))

            named_metric.append("?")
            grouped_param = []
            self.naming_url_parameters(rule["split"]["urlParams"], url_param, grouped_param)
            self.naming_url_parameters(rule["split"]["headerParams"], header_param, grouped_param)
            self.naming_url_parameters(rule["split"]["cookieParams"], cookie_param, grouped_param)
            named_metric.append("&".join(grouped_param))

            if rule['split']['method']:
                named_metric.append("(%s)" % method)

            return "".join(named_metric)

        return None


class TransactionTracerSettings(Settings):
    pass


class RumTraceSettings(Settings):
    pass


class MQ(Settings):
    pass


_settings = Settings()
_settings.transaction_tracer = TransactionTracerSettings()
_settings.error_collector = ErrorCollectorSettings()
_settings.action_tracer = ActionTracerSettings()
_settings.rum = RumTraceSettings()
_settings.naming = Naming([])
_settings.mq = MQ

# configure file
_settings.x_tingyun_id = "%s;c=1;x=%s;e=%s;s=%s"
_settings.app_name = "Python App"
_settings.plugins = ''  # split with ','
_settings.license_key = "This is default license"
_settings.enabled = True
_settings.log_file = None
_settings.log_level = logging.INFO
_settings.audit_mode = False
_settings.ssl = True
_settings.daemon_debug = False
_settings.host = "redirect.networkbench.com"
_settings.port = ''
_settings.tingyunIdSecret = ''
_settings.dataSentInterval = 60
_settings.applicationId = 'do-not-get-application-id'
_settings.appSessionKey = "do-not-get-session-key"
_settings.urls_merge = True
_settings.verify_certification = True
_settings.tornado_wsgi_adapter_mode = False

# for proxy
_settings.proxy_host = ''
_settings.proxy_port = ''
_settings.proxy_user = ''
_settings.proxy_pwd = ''
_settings.proxy_scheme = 'http'

# python environment variable
_settings.config_file = None
_settings.enable_profile = True
_settings.max_profile_depth = 600

# cross transaction trace
_settings.transaction_tracer.enabled = False

# internal use constance
_settings.shutdown_timeout = float(os.environ.get("TINGYUN_AGENT_SHUTDOWN_TIMEOUT", 2.5))
_settings.startup_timeout = float(os.environ.get("TINGYUN_AGENT_STARTUP_TIMEOUT", 0.0))
_settings.data_version = '1.2.0'
_settings.agent_version = get_version()
_settings.data_report_timeout = 15.0
_settings.stack_trace_count = 30  # used to limit the depth of action tracer stack
_settings.explain_plan_count = 30  # used to limit the depth of sql explain tracer stack
_settings.action_tracer_nodes = 2000
_settings.slow_sql_count = 20
_settings.action_apdex = {}
_settings.web_action_uri_params_captured = {}
_settings.external_url_params_captured = {}

# server configuration & some limitation about the data
# set the default value for it.
_settings.action_tracer.enabled = True
_settings.action_tracer.action_threshold = 2 * 1000  # 2s
_settings.action_tracer.top_n = 48
_settings.action_tracer.stack_trace_threshold = 500  # 500ms

_settings.action_tracer.slow_sql = True
_settings.action_tracer.slow_sql_threshold = 500
_settings.action_tracer.log_sql = False
_settings.action_tracer.explain_enabled = True
_settings.action_tracer.explain_threshold = 500  # 500ms
_settings.action_tracer.record_sql = "obfuscated"

# rum tracer settings default value
_settings.rum.enabled = False
_settings.rum.script = None
_settings.rum.sample_ratio = 1.0

_settings.auto_action_naming = True
_settings.urls_captured = []
_settings.ignored_params = []

_settings.error_collector.enabled = True
_settings.error_collector.ignored_status_codes = []

_settings.apdex_t = 500
_settings.capture_params = False
_settings.quantile = []
_settings.quantile_org = []
_settings.min_quantile_length = 4


# mq consumer
_settings.mq.enabled = False


_settings.log_level_mapping = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
}


def flatten_settings(settings):
    """get the iteration for setting item, include Settings object in Setting
    """

    def _flatten(settings_item, name, setting_object):
        for key, value in setting_object.__dict__.items():
            if key in filter_pro:
                console.debug("skip flatten property %s", key)
                continue

            if isinstance(value, Settings):
                if name:
                    _flatten(settings_item, '%s.%s' % (name, key), value)
                else:
                    _flatten(settings_item, key, value)
            else:
                if name:
                    settings_item['%s.%s' % (name, key)] = value
                else:
                    settings_item[key] = value

        return settings_item

    return _flatten({}, None, settings)


def get_upload_settings():
    """ construct the settings for upload to server
    :return: settings
    """
    dump_settings = {
        "nbs.license_key": _settings.license_key,
        "nbs.agent_enabled": _settings.enabled,
        "nbs.app_name": _settings.app_name,
        "nbs.auto_app_naming": False,
        "nbs.agent_log_file_name": _settings.log_file,
        "nbs.audit_mode": _settings.audit_mode,
        "nbs.agent_log_level": _settings.log_level,
        "nbs.proxy_host": _settings.proxy_host,
        "nbs.proxy_port": _settings.proxy_port,
        "nbs.proxy_user": _settings.proxy_user,
        "nbs.proxy_password": _settings.proxy_pwd,
        "nbs.host": _settings.host,
        "nbs.port": _settings.port,
        "nbs.ssl": _settings.ssl,
        "nbs.action_tracer.log_sql": _settings.action_tracer.log_sql,
        "nbs.daemon_debug": _settings.daemon_debug,
    }

    return dump_settings


def apply_config_setting(settings_object, name, value):
    target = settings_object
    fields = name.split('.', 1)

    while len(fields) > 1:
        # for additional Settings from server
        if not hasattr(target, fields[0]):
            setattr(target, fields[0], Settings())
        target = getattr(target, fields[0])
        fields = fields[1].split('.', 1)

    # transfer the string ignored ignored_status_codes to list
    if fields[0] == "ignored_status_codes" and value:
        try:
            value = [int(v) for v in value.strip().split(",")]
        except Exception as err:
            console.warning("got invalid ignore status code %s, errors %s", value, err)
    elif fields[0] == "ignored_status_codes" and not value:
        value = []

    # transfer the urls_captured to list
    # Warning in windows, the split with \n will get incorrect result
    if fields[0] == "urls_captured" and value:
        try:
            value = [re.compile(r"%s" % v) for v in value.strip().split("\n")]
        except Exception as err:
            console.warning("compile re url failed, %s, %s", value, err)
    elif fields[0] == "urls_captured" and not value:
        value = []

    # transfer the ignored_params to list
    if fields[0] == "ignored_params" and value:
        value = [str(v) for v in value.strip().split(",")]
    elif fields[0] == "ignored_params" and not value:
        value = []

    setattr(target, fields[0], value)


def uri_params_captured(original):
    """parse the web_action_uri_params_captured with protocal
    :param original:
    :return: formatted uri with param
    """
    uri_params = {}
    try:
        for uri_param in original.split('|'):
            parts = uri_param.split(",")
            uri = parts.pop(0).encode('utf-8')
            if not uri:
                continue

            uri_params[uri] = str(parts)
    except Exception as err:
        console.error("Parse the uri occurred errors. %s", err)

    return uri_params


def merge_settings(server_side_config=None):
    """
    :param server_side_config: the config downloaded from server
    :return: the merged settings
    """
    console.info("get the server side config %s", server_side_config)
    settings_snapshot = copy.deepcopy(_settings)
    global_conf_name = ["applicationId", "enabled", "appSessionKey", "dataSentInterval", "apdex_t", "tingyunIdSecret"]

    if not server_side_config:
        console.warning("update server config failed %s, local settings will be used.", server_side_config)
        return settings_snapshot

    # pop the structured config
    server_conf = server_side_config.pop("config", {})

    # get the individual settings
    if 'actionApdex' in server_side_config:
        original_apdex = server_side_config.pop("actionApdex", {})
        urls_apdexs = dict((key, original_apdex[key]) for key in original_apdex)
        action_apdex_urls = dict((key.encode("utf8"), urls_apdexs[key]) for key in urls_apdexs if key)

        server_side_config.update({"action_apdex": action_apdex_urls})

    for name in global_conf_name:
        if name not in server_side_config:
            console.warning("Lost server configure %s", name)
            continue

        apply_config_setting(settings_snapshot, name, server_side_config.get(name, ""))

    # transfer specified params captured with same uri
    if 'nbs.web_action_uri_params_captured' in server_conf:
        web_uri_params_captured = server_conf.pop("nbs.web_action_uri_params_captured", '')
        settings_snapshot.web_action_uri_params_captured = uri_params_captured(web_uri_params_captured)

    if 'nbs.external_url_params_captured' in server_conf:
        external_uri_params_captured = server_conf.pop("nbs.external_url_params_captured", '')
        settings_snapshot.external_url_params_captured = uri_params_captured(external_uri_params_captured)

    if 'nbs.quantile' in server_conf:
        quantile = server_conf.pop("nbs.quantile", '[]')
        try:
            quantile = json.loads(quantile)
        except Exception as err:
            console.error("Error type of quantile value %s, error %s", quantile, err)
        else:
            if len(quantile) != len(set(quantile)):
                console.warning("Error quantile value with duplicated %s", quantile)
            else:
                tmp = [v * 1.0 for v in quantile if str(v).isdigit()]
                if len(tmp) != len(quantile):
                    console.warning("quantile value is not digit.")
                else:
                    settings_snapshot.quantile_org = list(quantile)
                    settings_snapshot.quantile = tmp

    for item in server_conf:
        value = server_conf[item]
        # drop the first part of name with point
        start_pos = str(item).find('.') + 1
        apply_config_setting(settings_snapshot, item[start_pos:], value)

    console.info("return merged settings %s", settings_snapshot)
    return settings_snapshot


def global_settings():
    return _settings
