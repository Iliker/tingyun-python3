
"""transportation base tool for upload

"""

import time
import logging
import sys
import json
import zlib

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from tingyun.logistics.exceptions import DiscardDataForRequest, RetryDataForRequest, InvalidLicenseException
from tingyun.logistics.exceptions import InvalidDataTokenException, OutOfDateConfigException, ServerIsUnavailable
from tingyun.config.settings import global_settings
from tingyun.packages import six, requests

console = logging.getLogger(__name__)

# 10kbi
COMPRESS_MINIMUM_SIZE = 10 * 1024
USER_AGENT = ' NBS Newlens Agent/%s (python %s; %s)' % (global_settings().agent_version, sys.version.split()[0],
                                                        sys.platform)


def parse_proxy():
    """
    :return: {'http': 'xxx', 'https': 'xxx'}
    """
    settings = global_settings()

    # Proxy schema set in configure file,then use it
    # Else use `ssl` configure to decide 'http' or 'https'
    host = settings.proxy_host or ''
    port = settings.proxy_port or ''
    user = settings.proxy_user or ''
    scheme = settings.proxy_scheme or 'http'
    password = settings.proxy_pwd or ''

    # we support `http://user:password@host` format, so just checkout host
    if not host:
        return

    # urlparse will return <scheme>://<netloc>/<path>
    # (scheme, netloc, path, params, query, fragment)
    sections = urlparse.urlparse(host)
    if (not sections.scheme or sections.scheme not in ('http', 'https')) and not port:
        return

    path = ''
    netloc = host
    if sections.scheme:  # config the  host with <scheme>://<netloc>/<path> in settings
        scheme = sections.scheme
        netloc = sections.netloc
        path = sections.path
    elif sections.path:  # urlparse parse the netloc to path
        netloc = sections.path

    if port:
        netloc = "%s:%s" % (netloc, port)

    if user:
        if password:
            netloc = '%s:%s@%s' % (user, password, netloc)
        else:
            netloc = '%s@%s' % (user, netloc)

    full_url = '%s://%s%s' % (scheme, netloc, path)
    return {'http': full_url, 'https': full_url}


def transmitter(session, url, action, payload={}, param={}, audit_mode=False):
    """
    :param session: the request session to server
    :param url: the address witch data send to
    :param action: the send actually intention
    :param payload: request data
    :return: None
    """
    console.debug("Send request with url %s, action %s param %s", url, action, param)
    settings = global_settings()
    start_time = time.time()
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/octet-stream",
        "connection": "close",
        "Accept-Encoding": "deflate",
    }

    try:
        data = json.dumps(payload)
    except Exception as err:
        console.error("Encoding json for payload failed, url %s action %s param %s payload %s err %s",
                      url, action, param, payload, err)
        raise DiscardDataForRequest(str(sys.exc_info()[1]))

    if len(data) > COMPRESS_MINIMUM_SIZE:
        headers['Content-Encoding'] = 'deflate'
        level = (len(data) < 2000000) and 1 or 9
        data = zlib.compress(six.b(data), level)

    auto_close_session = False
    if not session:
        session = requests.session()
        auto_close_session = True

    content = ""
    try:
        # because of the root license use the sha1 encryption, the version of the certifi new than 2015.4.28
        # which used sha256 encryption, will cause the ssl verify failed, so no mater what kind of agent work
        # mode(private deploy or public use), we do not verify the ssl license now.

        verify_ssl = False if settings.port else settings.verify_certification
        timeout = settings.data_report_timeout
        proxy = parse_proxy()
        ret = session.post(url, data=data, params=param, headers=headers, timeout=timeout, verify=verify_ssl,
                           proxies=proxy)
        content = ret.content
    except requests.RequestException:
        console.error('Agent server is not attachable. if the error continues, please report to networkbench.'
                      'The error raised was %s. response content is %s.', sys.exc_info()[1], content)
        raise RetryDataForRequest(str(sys.exc_info()[1]))
    finally:
        duration = time.time() - start_time
        if auto_close_session:
            session.close()

    if audit_mode:
        console.info("Use %ss to upload data return value %r", duration, content)

    if ret.status_code == 400:
        console.error("Bad request has been submitted for url %s, please report this to us, thank u.", url)
        raise DiscardDataForRequest()
    elif ret.status_code == 503:
        console.error("Agent server is unavailable. This can be a transient issue because of the server or our core"
                      " application being restarted. if this error continues, please report to us. thank u.")
        raise DiscardDataForRequest()
    elif ret.status_code == 502:
        console.error("Agent server error, our engineer has caution this error, thanks for your support")
        raise ServerIsUnavailable("service unavailable, get status code 502")
    elif ret.status_code != 200:
        console.warning("We got none 200 status code %s, this maybe some network/server error, if this error continues,"
                        "please report to us . thanks for your support. return content %s", ret.status_code, ret)
        raise DiscardDataForRequest()

    try:
        if six.PY3:
            content = content.decode('UTF-8')

        result = json.loads(content)
    except Exception as err:
        console.warning("Decoding data for Json error. please contact us for further investigation. %s", err)
        raise DiscardDataForRequest(str(sys.exc_info()[1]))
    else:
        # successful exchange with server
        if result["status"] == "success":
            return result["result"] if "result" in result else []

    console.info("get unexpected return,  there maybe some issue. %s", result)
    server_status = int(result["result"]["errorCode"])

    if server_status == 460:
        console.warning("Invalid license key, Please contact to networkbench for more help.")
        raise InvalidLicenseException("Invalid license key")
    elif server_status == 462:
        console.warning("Invalid data format, maybe something get wrong when json encoding.")
        raise DiscardDataForRequest(content)
    elif server_status == 461:
        console.warning("Invalid data token, if this error continues, please report to networkbench support for further"
                        " investigation")
        raise InvalidDataTokenException()
    elif server_status == -1:
        console.warning("Agent server error, our engineer has caution this error, thanks for your support.")
        raise ServerIsUnavailable()
    elif server_status == 470:
        console.info("Configuration is out of date, server configuration will be obtain again")
        raise OutOfDateConfigException()

    return []
