"""
"""

from tingyun.config.settings import global_settings

tornado_version = ""

try:
    import tornado
    tornado_version = tornado.version
except Exception:
    pass


def defined_repertoire():
    """
    :return:
    """
    hookers = {
        "memcached": [
            {"target": "memcache", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_memcached'},
        ],

        "pymemcache": [
            {"target": "pymemcache.client", 'hook_func': "detect_base_client",
             'hook_module': 'tingyun.armoury.database_pymemcache'},
            {"target": "pymemcache.client", 'hook_func': "detect_pooled_client",
             'hook_module': 'tingyun.armoury.database_pymemcache'},
            {"target": "pymemcache.client.hash", 'hook_func': "detect_has_client",
             'hook_module': 'tingyun.armoury.database_pymemcache'},
        ],
        "bmemcached": [
            {"target": "bmemcached.client", 'hook_func': "detect_client",
             'hook_module': 'tingyun.armoury.database_bmemcache'},
        ],

        # mysql db
        "mysql": [
            {"target": "MySQLdb", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],
        "pymysql": [
            {"target": "pymysql", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],
        "oursql": [
            {"target": "oursql", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],

        # oracle
        "oracle": [
            {"target": "cx_Oracle", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],

        # postgres SQL
        "postgresql": [
            {"target": "postgresql.interface.proboscis.dbapi2", 'hook_func': 'detect',
             'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],
        # postgres SQL
        "psycopg2": [
            {"target": "psycopg2", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],
        "psycopg2ct": [
            {"target": "psycopg2ct", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],
        "psycopg2cffi": [
            {"target": "psycopg2cffi", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],

        # ODBC A Python DB API 2 module for ODBC
        "pyodbc": [
            {"target": "pyodbc", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.database_dbapi2'},
        ],

        # nosql mongodb
        "mongodb": [
            {"target": "pymongo.mongo_client", 'hook_func': 'detect_mongo_client',
             'hook_module': 'tingyun.armoury.database_mongo'},
            {"target": "pymongo.connection", 'hook_func': 'detect_connection',
             'hook_module': 'tingyun.armoury.database_mongo'},
            {"target": "pymongo.collection", 'hook_func': 'detect_collection',
             'hook_module': 'tingyun.armoury.database_mongo'},
        ],

        # nosql redis
        "redis": [
            {"target": "redis.connection", 'hook_func': 'detect_connection',
             'hook_module': 'tingyun.armoury.database_redis'},
            {"target": "redis.client", 'hook_func': 'detect_client_operation',
             'hook_module': 'tingyun.armoury.database_redis'},
        ],

        # external call
        "urllib": [
            {"target": "urllib", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.external_urllib'},
        ],
        "urllib2": [
            {"target": "urllib2", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.external_urllib2'},
        ],
        # v1.6-v1.14
        "urllib3": [
            {"target": "urllib3.poolmanager", 'hook_func': 'detect', 'hook_module': 'tingyun.armoury.external_urllib3'},
        ],
        # 0.8.0-0.9.3
        "thrift": [
            {"target": "thrift.transport.TSocket", 'hook_func': 'detect_tsocket',
             'hook_module': 'tingyun.armoury.external_thrift'},
            {"target": "thrift.transport.TSSLSocket", 'hook_func': 'detect_tsslsocket',
             'hook_module': 'tingyun.armoury.external_thrift'},
        ],

        # 2.0.0-2.10.0
        "requests": [
            {"target": "requests.sessions", 'hook_func': 'detect_requests_sessions',
             'hook_module': 'tingyun.armoury.external_requests'},
        ],
        # 0.7.5-0.9.2
        "httplib2": [
            {"target": "httplib2", 'hook_func': 'detect_httplib2_http',
             'hook_module': 'tingyun.armoury.external_httplib2'},
            {"target": "httplib2", 'hook_func': 'detect_http_connect_with_timeout',
             'hook_module': 'tingyun.armoury.external_httplib2'},
            {"target": "httplib2", 'hook_func': 'detect_https_connect_with_timeout',
             'hook_module': 'tingyun.armoury.external_httplib2'},
        ],

        # django, this weapon must not be removed.
        "django": [
            {"target": "django.core.handlers.base", 'hook_func': 'detect_middleware',
             'hook_module': 'tingyun.armoury.framework_django'},
            {"target": "django.core.handlers.wsgi", 'hook_func': 'detect_wsgi_entrance',
             'hook_module': 'tingyun.armoury.framework_django'},
            {"target": "django.core.urlresolvers", 'hook_func': 'detect_urlresolvers',
             'hook_module': 'tingyun.armoury.framework_django'},
            {"target": "django.views.generic.base", 'hook_func': 'detect_views_dispatch',
             'hook_module': 'tingyun.armoury.framework_django'},

            {"target": "django.template.loader_tags", 'hook_func': 'detect_template_block_render',
             'hook_module': 'tingyun.armoury.framework_django'},
            {"target": "django.template.base", 'hook_func': 'detect_django_template',
             'hook_module': 'tingyun.armoury.framework_django'},

            {"target": "django.http.multipartparser", 'hook_func': 'detect_http_multipartparser',
             'hook_module': 'tingyun.armoury.framework_django'},

            {"target": "django.core.mail", 'hook_func': 'detect_core_mail',
             'hook_module': 'tingyun.armoury.framework_django'},
            {"target": "django.core.mail.message", 'hook_func': 'detect_core_mail_message',
             'hook_module': 'tingyun.armoury.framework_django'},
        ],

        # django-piston, 0.2.2.1-0.2.3
        "piston": [
            {"target": "piston.resource", 'hook_func': 'detect_piston_resource',
             'hook_module': 'tingyun.armoury.ammunition.piston'},
        ],

        # flask, 0.6-1.0
        "flask": [
            {"target": "flask.app", 'hook_func': 'detect_wsgi_entrance',
             'hook_module': 'tingyun.armoury.framework_flask'},
            {"target": "flask.app", 'hook_func': 'detect_app_entrance',
             'hook_module': 'tingyun.armoury.framework_flask'},
            {"target": "flask.blueprints", 'hook_func': 'detect_app_blueprint_entrance',
             'hook_module': 'tingyun.armoury.framework_flask'},
            {"target": "flask.templating", 'hook_func': 'detect_templates',
             'hook_module': 'tingyun.armoury.framework_flask'},
        ],

        # jinja2 2.3-2.8
        'jinja2': [
            {"target": "jinja2.loaders", 'hook_func': 'detect_template_loader',
             'hook_module': 'tingyun.armoury.template_jinja2'},
            {"target": "jinja2.environment", 'hook_func': 'detect_jinja2',
             'hook_module': 'tingyun.armoury.template_jinja2'},
            ],

        # version 2.8.1-2.12.x
        'web2py': [
            {"target": "gluon.main", 'hook_func': 'detect_wsgi_entrance',
             'hook_module': 'tingyun.armoury.framework_web2py'},
            {"target": "gluon.compileapp", 'hook_func': 'detect_compileapp',
             'hook_module': 'tingyun.armoury.framework_web2py'},
            {"target": "gluon.template", 'hook_func': 'detect_template',
             'hook_module': 'tingyun.armoury.framework_web2py'},
        ],

        # version 0.3.x
        'webpy': [
            {"target": "web.application", 'hook_func': 'detect_wsgi_entrance',
             'hook_module': 'tingyun.armoury.framework_webpy'},

            {"target": "web.application", 'hook_func': 'detect_application',
             'hook_module': 'tingyun.armoury.framework_webpy'},
        ],

        # version 4.x.x
        # when tornado only use as wsgi application, do not detect tornado component
        "tornado4": [
            {"target": "tornado.web", 'hook_func': 'detect_web',
             'hook_module': 'tingyun.armoury.ammunition.tornado.web'},

            {"target": "tornado.httputil", 'hook_func': 'detect_tracker_entrance',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.http_util'},
            {"target": "tornado.httpserver", 'hook_func': 'detect_tracker_export',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.http_server'},
            {"target": "tornado.httpclient", 'hook_func': 'detect_http_client',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.http_client'},
            {"target": "tornado.gen", 'hook_func': 'detect_gen',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.gen'},
            {"target": "tornado.ioloop", 'hook_func': 'detect_ioloop',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.ioloop'},
            {"target": "tornado.concurrent", 'hook_func': 'detect_concurrent',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.concurrent'},
            {"target": "concurrent.futures", 'hook_func': 'detect_concurrent',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.concurrent'},
            {"target": "tornado.stack_context", 'hook_func': 'detect_stack_context',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.stack_context'},
        ]if "4." in tornado_version and not global_settings().tornado_wsgi_adapter_mode else [],

        "tornado-wsgi-adapter-mode": [
            {"target": "tornado.web", 'hook_func': 'detect_handlers',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.wsgi_mode.web'},
            {"target": "tornado.httpclient", 'hook_func': 'detect_http_client',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.wsgi_mode.http_client'},
            {"target": "tornado.wsgi", 'hook_func': 'detect_wsgi_entrance',
             'hook_module': 'tingyun.armoury.ammunition.tornado_4.wsgi_mode.wsgi'},
        ]if "4." in tornado_version and global_settings().tornado_wsgi_adapter_mode else [],

        # mako v0.7.x-v1.0.x
        "mako": [
            {"target": "mako.template", 'hook_func': 'detect_template',
             'hook_module': 'tingyun.armoury.template_mako'},
        ],

        # 0.13.0-1.0.2
        "gevent": [
            {"target": "gevent.pywsgi", 'hook_func': 'detect_wsgi',
             'hook_module': 'tingyun.armoury.matrix.t_gevent'},
            {"target": "gevent.wsgi", 'hook_func': 'detect_pywsgi',
             'hook_module': 'tingyun.armoury.matrix.t_gevent'},
        ],

        # openstack-nova
        'openstack-nova': [
            # nova.api.openstack.wsgi
            {"target": "nova.api.openstack.wsgi", 'hook_func': 'resource_wsgi_entrance',
             'hook_module': 'tingyun.armoury.nova.api_openstack_wsgi'},

            # nova.wsgi
            {"target": "nova.wsgi", 'hook_func': 'middleware_wsgi_entrance',
             'hook_module': 'tingyun.armoury.nova.wsgi'},
            {"target": "nova.wsgi", 'hook_func': 'router_wsgi_entrance',
             'hook_module': 'tingyun.armoury.nova.wsgi'},

            # nova.api.auth
            {"target": "nova.api.auth", 'hook_func': 'keystone_context_wsgi_entrance',
             'hook_module': 'tingyun.armoury.nova.api_auth'},

            # nova.api.ec2
            {"target": "nova.api.ec2", 'hook_func': 'ec2_keystone_wsgi_entrance',
             'hook_module': 'tingyun.armoury.nova.api_ec2'},
            {"target": "nova.api.ec2", 'hook_func': 'requestify_wsgi_entrance',
             'hook_module': 'tingyun.armoury.nova.api_ec2'},
            {"target": "nova.api.ec2", 'hook_func': 'authorizer_wsgi_entrance',
             'hook_module': 'tingyun.armoury.nova.api_ec2'},
            {"target": "nova.api.ec2", 'hook_func': 'executor_wsgi_entrance',
             'hook_module': 'tingyun.armoury.nova.api_ec2'},

            # webob.client
            {"target": "webob.client", 'hook_func': 'send_request_wsgi_entrance',
             'hook_module': 'tingyun.armoury.webob.client'},
            {"target": "webob.response", 'hook_func': 'response_wsgi_entrance',
             'hook_module': 'tingyun.armoury.webob.response'},
        ],
        # bottle 0.10.x-0.12.x
        "bottle": [
            {"target": "bottle", 'hook_func': 'detect_wsgi_entrance',
             'hook_module': 'tingyun.armoury.framework_bottle'},
            {"target": "bottle", 'hook_func': 'detect_templates',
             'hook_module': 'tingyun.armoury.framework_bottle'},
            {"target": "bottle", 'hook_func': 'detect_app_components',
             'hook_module': 'tingyun.armoury.framework_bottle'},
        ],

        # RabbitMQ pika0.10.x-
        "pika": [
            {"target": "pika.adapters.blocking_connection", 'hook_func': 'detect_block_channel',
             'hook_module': 'tingyun.armoury.mq.mq_pika'},
            {"target": "pika.channel", 'hook_func': 'detect_channel',
             'hook_module': 'tingyun.armoury.mq.mq_pika'},
            {"target": "pika.connection", 'hook_func': 'detect_connection',
             'hook_module': 'tingyun.armoury.mq.mq_pika'},
        ]
    }

    return hookers
