
"""used to define console output destination
"""

import sys
import logging
import logging.handlers
from tingyun.packages.wrapt.decorators import synchronized


class _NullHandler(logging.Handler):
    def emit(self, record):
        pass

console = logging.getLogger('tingyun')
console.addHandler(_NullHandler())
_LOG_FORMAT = '%(asctime)s (%(process)d/%(threadName)s) %(name)s %(lineno)s %(levelname)s - %(message)s'
_initialized = False


@synchronized
def initialize_logging(log_file, log_level):
    global _initialized
    if _initialized:
        console.warning("The logging %s was initialized ever.", log_file)
        return 1

    try:
        is_file_log = False
        handler = logging.StreamHandler(sys.stdout)
        if log_file == 'stdout':
            console.info('Initializing Python agent stdout logging.')
        elif log_file == 'stderr':
            handler = logging.StreamHandler(sys.stderr)
            console.info('Initializing Python agent stderr logging.')
        elif log_file:
            try:
                handler = logging.FileHandler(log_file)
                is_file_log = True
                console.info("init log file %s", log_file)
            except Exception as _:
                handler = logging.StreamHandler(sys.stderr)
                console.exception('Create log file %s failed. the tingyun log will be output to stderr.' % log_file)

        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        console.addHandler(handler)
        console.setLevel(log_level)

        if is_file_log:
            console.propagate = False

        _initialized = True
    except Exception as err:
        console.error("Errors occurred when init agent log. %s", err)

    return 0
