# -*- coding: utf-8 -*-

"""define the interface for browser monitor.
    this should follow the protocol pep333: https://www.python.org/dev/peps/pep-0333/#the-start-response-callable
"""

import re
import logging
import random


console = logging.getLogger(__name__)

html_re = re.compile(b'<html[^>]*>', re.IGNORECASE)
head_re = re.compile(b'<head[^>]*>.*</head>', re.IGNORECASE | re.DOTALL)
body_re = re.compile(b'<body[^>]*>', re.IGNORECASE)
title_re = re.compile(b'<title[^>]*>.*</title>', re.IGNORECASE | re.DOTALL)


class TingYunWSGIBrowserRumMiddleware(object):
    """More information come with pep333: https://www.python.org/dev/peps/pep-0333
    """
    def __init__(self, tracker, application, start_response, environ):
        self.tracker = tracker
        self.ignore_rum = True
        self.application = application
        self.environ = environ
        self.org_start_response = start_response
        self.sample_ratio = 0.0
        self.enable = self.is_enable_auto_rum()
        self.allowed_content = ['text/html']

        self.status = None
        self.response_headers = []
        self.content_length = None
        self.args = ()
        self.writer = None

    def is_enable_auto_rum(self):
        if not self.tracker.enabled or not self.tracker.settings:
            console.debug("setting not enable browser insert. %s, %s", self.tracker.enabled, self.tracker.settings)
            return False

        if not self.tracker.settings.rum.enabled:
            console.debug("Server rum disabled.")
            return False

        # get ajax request, local auto rum is disabled.
        if not self.tracker.rum_enabled:
            console.debug("Get Ajax request, disable auto insert browser agent.")
            return False

        self.sample_ratio = self.tracker.settings.rum.sample_ratio
        if self.sample_ratio < random.random():
            console.debug("sample ratio decide ignore auto insert. %s", self.sample_ratio)
            return False

        return True

    def write_headers(self):
        """
        :return:
        """
        header = []
        if self.content_length is not None:
            for key, value in self.response_headers:
                if key != 'Content-Length':
                    header.append((key, value))
                else:
                    # data length changed by agent.
                    header.append((key, "%s" % self.content_length))

            self.response_headers = header

        self.writer = self.org_start_response(self.status, self.response_headers, *self.args)

    def write(self, data):
        """define this for delay call real start_response func.
            WSGI specification define the func just for compatible with old version framework.

            This func should not be used, but some old framework may use it. so avoid some issue, skip auto insert js.
        :return:
        """
        self.ignore_rum = True

        if not self.writer:
            self.write_headers()

        console.debug("framework use the write method..")
        return self.writer(data)

    def start_response(self, status, response_headers, *args):
        """Note: The application may call start_response more than once,
                 if and only if the exc_info argument is provided.
            It is a fatal error to call start_response without the exc_info argument
            if start_response has already been called within the current invocation of the application
        :return: write func which returned by wsgi start_response
        """
        self.status = status
        self.response_headers = response_headers
        self.args = args
        enabled = self.is_enable_auto_rum()
        header_dict = dict([(str(key).lower(), value) for (key, value) in response_headers])

        if not enabled:
            self.write_headers()
            self.ignore_rum = True
            return self.write

        def is_insertable():
            """follow rules will return false
               . content specified encoding, wsgi application should not return encoded response
                    and maybe has some performance issue
               . attachment for file download
               . content-type is not html response
               . invalid content-length
            """
            # non-200 response, disabled
            if '200' not in status:
                console.debug("Non-200 status code, ignore auto insert browser agent. %s", status)
                return False

            if 'content-length' in header_dict:
                try:
                    int(header_dict['content-length'])
                except ValueError:
                    cl = header_dict.get("content-length")
                    console.debug("Invalid content-length feature. %s, type %s", cl, type(cl))
                    return False

            # None/invalid/non-html content-type will be ignored
            content_type = header_dict.get("content-type", None)
            if not content_type or content_type.split(';')[0] not in self.allowed_content:
                console.debug("Invalid content type %s", content_type)
                return False

            content_disposition = header_dict.get('content-disposition', None)
            if content_disposition is not None and content_disposition.split(';')[0].strip().lower() == 'attachment':
                console.info("Get download file request, ignore auto insert browser agent.")
                return False

            return True

        if is_insertable():
            self.ignore_rum = False
            self.content_length = header_dict.get('content-length', None)

        if self.ignore_rum:
            self.ignore_rum = True
            self.write_headers()
            return self.write

        # at last. we return the Compatible write just for delay call start_response for avoiding the gateway/server
        # flush the header when first iterable data prepared.
        # and we will change the data length if it exist.
        return self.write

    def do_auto_monitor(self, data):
        """
        :param data: response data.
        :return:
        """
        buffer_data = self.insert_js_to_html(data, self.tracker.fork_browser_js_head())
        insert_data_length = len(buffer_data) - len(data)

        if self.content_length and insert_data_length:
            self.content_length = int(self.content_length)
            self.content_length += insert_data_length

        # we just check for the first data block with 64kb
        self.ignore_rum = True
        return insert_data_length, buffer_data

    def __call__(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return:
        """
        for ret in self.application(self.environ, self.start_response):
            # maybe some blocks are not header parts.
            if self.ignore_rum:
                console.debug("Ignore auto browser signed.")
                yield ret
                continue

            # WSGI specification note: start_response should not be called before get first block of data.
            # just do insert the js when headers are not send because we need to change the length if necessary.
            if not self.writer:
                if not ret:
                    continue

                _, buffer_data = self.do_auto_monitor(ret)
                self.write_headers()
                self.ignore_rum = True
                yield buffer_data
            else:
                console.debug("Warning! Ignore the rum because of headers are send before.")
                yield ret

        if not self.writer:
            self.write_headers()
            self.ignore_rum = True

    def insert_js_to_html(self, data, agent_js, search_size=65536):
        """
        :param data: block data sent to gateway
        :param agent_js: javascript agent html label & content
        :param search_size: 1024 * 64 = 64Kb
        :return:
        """
        html = html_re.search(data[:search_size])
        if not html:
            console.debug("Content is not html context, ignore it")
            return data

        body = body_re.search(data[:search_size])
        if not body:
            console.debug("No body label in data block(first 64k), ignore it")
            return data

        head_meta = head_re.search(data[:search_size])
        if not head_meta:
            console.debug("No head label found in data block(first 64k), ignore it")
            return data

        def combine_data(position):
            return b''.join((data[:position], agent_js, data[position:]))

        title = title_re.search(data[:search_size])
        if title:
            console.debug("Insert browser agent after title label.")
            return combine_data(title.end())

        head_meta = head_re.search(data[:search_size])
        if head_meta:
            console.debug("Insert browser agent before head end label.")
            return combine_data(head_meta.end() - len("</head>"))
