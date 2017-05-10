# -*- coding: utf-8 -*-

"""The detect module follow the protocol: https://www.python.org/dev/peps/pep-0249/

"""

import re
import logging

from tingyun.armoury.ammunition.tracker import current_tracker
from tingyun.armoury.ammunition.database_tracker import DatabaseTracker
from tingyun.armoury.ammunition.function_tracker import FunctionTracker, wrap_function_trace

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse


# module_name: standard db name for data exchange protocol.
# 数据库类型协议，参考文档
DB_TYPE_MYSQL = "MySQL"
DB_TYPE_ORACLE = "Oracle"
DB_TYPE_POSTGRELSQL = "PostgreSQL"
DB_TYPE_SQLSERVER = "SQLServer"
db_name_module = {
    "MySQLdb": DB_TYPE_MYSQL, "pymysql": DB_TYPE_MYSQL, "oursql": "MySQL",
    "cx_Oracle": DB_TYPE_ORACLE,
    "psycopg2": DB_TYPE_POSTGRELSQL, "psycopg2ct": DB_TYPE_POSTGRELSQL, "psycopg2cffi": DB_TYPE_POSTGRELSQL,
    "pyodbc": DB_TYPE_SQLSERVER
    }
console = logging.getLogger(__name__)


def detect(module):
    """ more interface description about dbapi2 in: https://www.python.org/dev/peps/pep-0249/
    :param module:
    :return:
    """
    dbtype = db_name_module.get(getattr(module, "__name__", "DBAPI2"))

    def parse_connect_params(connect_params):
        """解析连接数据库的host、port信息，支持mysql-python、pymysql、oursql、cx_Oracle插件
            根据数据库分类来分类获取port信息
            mysql-python:
                connect(host, user, pwd, port, db)
            pymysql
                connect(host=None, port=0, database=None)
            oursql http://pythonhosted.org/oursql：
                oursql.connect(host='127.0.0.1', user='habnabit', passwd='foobar',
                db='example', port=3307)
        :param connect_params:
        :return:
        """
        host, port, db_name = 'Unknown', 'Unknown', 'Unknown'
        if not connect_params or len(connect_params) != 2:
            return

        _args = connect_params[0] or ()
        _kwargs = connect_params[1] or {}

        if dbtype == DB_TYPE_MYSQL:
            # 遵循DBAPI2协议前5个参数都是host=None, user=None, password="", database=None, port=0
            host, port = _kwargs.get('host'), _kwargs.get('port')
            db_name = _kwargs.get('database') or _kwargs.get('db')

            if not host:
                host = _args[0] if len(_args) >= 1 else "Unknown"

            if not port:
                port = _args[4] if len(_args) >= 5 else 3306
            else:
                port = 3306

            if not db_name:
                db_name = _args[3] if len(_args) >= 4 else "Unknown"

        elif dbtype == DB_TYPE_ORACLE:
            # cx_Oracle.connect('hr', 'hrpwd', 'localhost:1521/XE') 或者
            # '(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=oracle.db.com)(PORT=1521)))\
            # (CONNECT_DATA=(SID=nbsdb)))'
            if 3 == len(_args):
                con_info = re.findall(r'^(.+?):(.+?)/(.+?)$', str(_args[2]), re.IGNORECASE)
                if not con_info:
                    con_info = re.findall(r'^.*HOST=(.+?)\).*PORT=(.+?)\).*SID=(.+?)\).?', str(_args[2]), re.IGNORECASE)

                if con_info and 3 == len(con_info[0]):
                    host, port, db_name = con_info[0]

            # 'hr/hrpwd@localhost:1521/XE'
            if 1 == len(_args):
                con_str = str(_args[0])
                _host = con_str[con_str.find("@") + 1: con_str.find(":")]
                _port = con_str[con_str.find(":") + 1: con_str.rfind("/")]
                _db_name = con_str[con_str.rfind("/") + 1:]

                if _host and _port and _db_name:
                    host, port, db_name = _host, _port, _db_name

        elif dbtype == DB_TYPE_POSTGRELSQL:
            # 链接方式doc: https://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING
            # postgresql://localhost/mydb
            # postgresql://localhost:5432/mydb
            # dsn参数: host=localhost port=5432 dbname=mydb connect_timeout=10
            # 关键字参数
            # todo: 不支持以下链接方式：
            # 不完整的URI连接， postgresql:///mydb?host=localhost&port=5433
            # IPV4, postgresql://[2001:db8::1234]/database
            # 环境变量方式： https://www.postgresql.org/docs/current/static/libpq-envars.html
            _host, _port, _db_name = None, None, None

            if not _kwargs or len(_kwargs) == 1:
                con_str = _args[0] if 1 == len(_args) and not _kwargs else _kwargs.get('dsn', "")

                # host=localhost port=5432 dbname=mydb connect_timeout=10
                if "//" not in con_str:
                    for kv in con_str.split():
                        k, v = kv.split('=')
                        if k.lower() not in ["host", "port", "dbname"]:
                            continue

                        if 'host' == k.lower():
                            _host = v
                        elif 'port' == k.lower():
                            _port = v
                        elif 'dbname' == k.lower():
                            _db_name = v

                else:
                    # postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]
                    con_str = _args[0] if 1 == len(_args) and not _kwargs else _kwargs.get('dsn', "")
                    sections = urlparse.urlparse(con_str)

                    if sections.netloc:
                        if "@" in sections.netloc:
                            host_port = sections.netloc.split("@")[1]
                        else:
                            host_port = sections.netloc

                        parts = host_port.split(":")
                        if len(parts) == 2:
                            _host, _port = parts[0], parts[1]
                        elif len(parts) == 1:
                            _host, _port = parts[0], 5432

                        _db_names = sections.path.replace('/', '', 1).split('?')
                        _db_name = _db_names[0] if len(_db_names) >= 1 else sections.path
            else:
                _host, _port = _kwargs.get("host"), _kwargs.get("port") or 5432
                _db_name = _kwargs.get("database") or _kwargs.get("dbname")

            host, port, db_name = _host or 'Unknown', _port or 5432, _db_name or 'Unknown'

        elif dbtype == DB_TYPE_SQLSERVER:
            # pyodbc 包仅支持sqlServer数据的抓取，其他类型无法识别，也几乎没人会用这么复杂的包连接别的数据库
            if len(_args) >= 1 and 'DSN' not in str(_args[0]).upper():
                # 'DSN=test;PWD=password',如果用户使用了DSN，无法抓取该信息
                # ('DRIVER={FreeTDS};SERVER=sqlserver.db.com; PORT=1433;DATABASE=python_test;
                # UID=leng;PWD=Windows2008',)
                # 仅支持表中的一种port，host写法,不区分大小写
                _host = re.findall(r"SERVER=(.+?);", str(_args[0]), re.IGNORECASE)
                _port = re.findall(r"port=(.+?);", str(_args[0]), re.IGNORECASE)
                _db_name = re.findall(r"DATABASE=(.+?);", str(_args[0]), re.IGNORECASE)

                _host, _port = _host[0] if _host else None, _port[0] if _port else None
                _db_name = _db_name[0] if _db_name else None

                # 会出现'DRIVER={FreeTDS};SERVER=sqlserver.db.com,1433;DATABASE=python_test;UID=leng;PWD=Windows2008'
                if _host and _db_name and not _port:
                    parts = str(_host).split(",")
                    if 2 == len(parts):
                        _host = parts[0].strip()
                        _port = parts[1].strip()

                host, port, db_name = _host or 'Unknown', _port or 'Unknown', _db_name or 'Unknown'
        else:
            logging.debug("Not support database type for capture ip & port.")

        return host, port, db_name

    class TingYunCursor(object):

        def __init__(self, cursor, cursor_params=None, connect_params=None):
            """https://docs.python.org/2.7/reference/datamodel.html?highlight=object.__setattr__#object.__setattr__
            :param cursor:
            :param cursor_params:
            :param connect_params:
            :return:
            """
            object.__setattr__(self, 'cursor', cursor)
            object.__setattr__(self, 'cursor_params', cursor_params)
            object.__setattr__(self, 'connect_params', connect_params)

            host, port, db_name = parse_connect_params(connect_params)

            object.__setattr__(self, 'host', host)
            object.__setattr__(self, 'port', port)
            object.__setattr__(self, 'db_name', db_name)

        def __setattr__(self, name, value):
            setattr(self.cursor, name, value)

        def __getattr__(self, name):
            return getattr(self.cursor, name)

        def __iter__(self):
            return iter(self.cursor)

        def fetchone(self, *args, **kwargs):
            """we do not capture the metric of execute result. this is small time used
            :args:
            :kwargs:
            :return:
            """
            return self.cursor.fetchone(*args, **kwargs)

        def fetchmany(self, *args, **kwargs):
            """we do not capture the metric of execute result. this is small time used
            :args:
            :kwargs:
            :return:
            """
            return self.cursor.fetchmany(*args, **kwargs)

        def fetchall(self, *args, **kwargs):
            """this operation maybe spend more time. this is small time used
            and the sql was executed. we can not take it
            :args:
            :kwargs:
            :return:
            """
            return self.cursor.fetchall(*args, **kwargs)

        def execute(self, sql, *args, **kwargs):
            """
            :param sql:
            :param args:
            :param kwargs:
            :return:
            """
            tracker = current_tracker()
            if not tracker:
                return self.cursor.execute(sql, *args, **kwargs)

            with DatabaseTracker(tracker, sql, dbtype, module, self.connect_params, self.cursor_params,
                                 (args, kwargs), host=self.host, port=self.port, db_name=self.db_name):
                return self.cursor.execute(sql, *args, **kwargs)

        def executemany(self, sql, *args, **kwargs):
            """
            :param sql:
            :param args:
            :param kwargs:
            :return:
            """
            tracker = current_tracker()
            if not tracker:
                return self.cursor.executemany(sql, *args, **kwargs)

            with DatabaseTracker(tracker, sql, dbtype, module, host=self.host, port=self.port, db_name=self.db_name):
                return self.cursor.executemany(sql, *args, **kwargs)

        def callproc(self, procname, *args, **kwargs):
            """
            :param procname:
            :param args:
            :param kwargs:
            :return:
            """
            tracker = current_tracker()
            if not tracker:
                return self.cursor.callproc(procname, *args, **kwargs)

            with DatabaseTracker(tracker, 'CALL %s' % procname, dbtype, module, host=self.host, port=self.port,
                                 db_name=self.db_name):
                return self.cursor.callproc(procname, *args, **kwargs)

    class TingYunConnection(object):

        def __init__(self, connection, params=None):
            """
            :param connection:
            :param params:
            :return:
            """
            object.__setattr__(self, 'connection', connection)
            object.__setattr__(self, 'params', params)
            host, port, db_name = parse_connect_params(params)

            object.__setattr__(self, 'host', host)
            object.__setattr__(self, 'port', port)
            object.__setattr__(self, 'db_name', db_name)

        def __setattr__(self, name, value):
            setattr(self.connection, name, value)

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def close(self, *args, **kwargs):
            """
            :param args:
            :param kwargs:
            :return:
            """
            return self.connection.close(*args, **kwargs)

        def cursor(self, *args, **kwargs):
            """
            :param args:
            :param kwargs:
            :return:
            """
            return TingYunCursor(self.connection.cursor(*args, **kwargs), (args, kwargs), self.params)

        def commit(self):
            """
            :return:
            """
            tracker = current_tracker()
            if not tracker:
                return self.connection.commit()

            with DatabaseTracker(tracker, 'COMMIT', dbtype, module, host=self.host, port=self.port,
                                 db_name=self.db_name):
                return self.connection.commit()

        def rollback(self):
            """
            :return:
            """
            tracker = current_tracker()
            if not tracker:
                return self.connection.rollback()

            with DatabaseTracker(tracker, 'ROLLBACK', dbtype, module, host=self.host, port=self.port,
                                 db_name=self.db_name):
                return self.connection.rollback()

    class DatabaseWrapper(object):

        def __init__(self, connect):
            self.connect = connect
            self.connect_instance = None

        def __call__(self, *args, **kwargs):
            """when module call the connect method. the wrapper will callback __call__ instead.
            :param args:
            :param kwargs:
            :return:
            """
            self.connect_instance = self.connect(*args, **kwargs)

            return TingYunConnection(self.connect_instance, (args, kwargs))

    # Check if module is already wrapped
    if hasattr(module, '_self_dbapi2_wrapped'):
        return

    wrap_function_trace(module, 'connect', name='%s.connect' % dbtype, group='Database')
    module.connect = DatabaseWrapper(module.connect)
    module._self_dbapi2_wrapped = True
