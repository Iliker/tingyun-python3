
"""This module define some user api for manually use the tingyun python agent.

    We will do the best to providing more convenient usage and available description about api, more detail will be as
a extension in user usage documentation
"""

import tingyun.embattle
import tingyun.armoury.trigger.wsgi_entrance
import tingyun.armoury.ammunition.function_tracker


"""
   Description: Init the agent for detecting all of the python plugins that can be detected, more detail listed in
                agent doc `framework support` chapter.)

   Warning: The init action must be called before all of your python code. Or the agent maybe can not work well.

   Usage:

       from tingyun.api import init_tingyun_agent

       init_tingyun_agent(config_file=None)

   Param:
       config_file: The absolutely path of tingyun agent config file.  if the option is not provided, you should set
                    the environment variable `TING_YUN_CONFIG_FILE`, or the agent will not work.
"""
init_tingyun_agent = tingyun.embattle.initialize


"""
    Description: A wrapper only used to wsgi application entrance.

    Usage:

        # init the tingyun agent first
        from tingyun.api import init_tingyun_agent
        from tingyun.api import wsgi_app_decorator

        init_tingyun_agent(config_file='/tmp/tingyun.ini')

        @wsgi_app_decorator(framework='xx', version='xx')
        def application(environ, start_response):
            status = '200 OK' # HTTP Status
            headers = [('Content-type', 'text/plain')] # HTTP Headers
            start_response(status, headers)

            # The returned object is going to be printed
            return ["Hello World"]

    Params:
        framework: this param indicate witch framework your application used. decorator has default value-`xx` for
                   this parameter.
        version: the version of the framework. decorator has default value-`xx` for this parameter.
"""
wsgi_app_decorator = tingyun.armoury.trigger.wsgi_entrance.wsgi_application_decorator


"""
    Description: A wrapper used to collect function metric performance data. this function should be used after function
                 init_tingyun_agent() and wsgi_app_decorator()

    Usage:
        from tingyun.api import init_tingyun_agent
        from tingyun.api import wsgi_app_decorator
        from tingyun.api import function_trace_decorator

        init_tingyun_agent(config_file='/tmp/tingyun.ini')

        @wsgi_app_decorator(framework='xx', version='xx')
        def application(environ, start_response):
            status = '200 OK' # HTTP Status
            headers = [('Content-type', 'text/plain')] # HTTP Headers
            start_response(status, headers)

            return ["Hello World"]

        import hashlib

        @function_trace_decorator(name='md5sum', group='calculator')
        def md5sum(filename):
            fd = open(filename,"r")
            fcont = fd.r
            fd.close()
            fmd5 = hashlib.md5(fcont)
            return fmd5

    Params: both parameter can be `None`, we will set default value for it.
        name: the name of the function or some meaningful to you.
        group: the group of the function belong to. or some meaningful to you
"""
function_trace_decorator = tingyun.armoury.ammunition.function_tracker.function_trace_decorator
