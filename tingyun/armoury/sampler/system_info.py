"""This module implements functions for querying properties of the operating
system or for the specific process the code is running in.

"""

import os
import sys
import multiprocessing
import re

try:
    import resource
except ImportError:
    pass


def cpu_count():
    """Returns the number of CPUs in the system.

    """
    # The multiprocessing module support Windows, BSD systems  MacOS X and systems which support the POSIX API
    try:
        return multiprocessing.cpu_count()
    except NotImplementedError:
        pass

    # For Jython, we need to query the Java runtime environment.
    try:
        from java.lang import Runtime
        runtime = Runtime.getRuntime()
        res = runtime.availableProcessors()
        if res > 0:
            return res
    except ImportError:
        pass

    # Solaris system
    try:
        pseudoDevices = os.listdir('/devices/pseudo/')
        expr = re.compile('^cpuid@[0-9]+$')

        res = 0
        for pd in pseudoDevices:
            if expr.match(pd) != None:
                res += 1

        if res > 0:
            return res
    except OSError:
        pass

    return 1


def memory_total():
    """Returns the total physical memory available in the system.

    """
    # For Linux we can determine it from the proc filesystem.
    if sys.platform == 'linux2':
        try:
            parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')

            with open('/proc/meminfo') as fp:
                try:
                    for line in fp.readlines():
                        match = parser.match(line)
                        if not match:
                            continue
                        key, value = match.groups(['key', 'value'])
                        if key == 'MemTotal':
                            memory_bytes = float(value) * 1024
                            return memory_bytes / (1024*1024)
                except Exception as _:
                    pass
        except IOError:
            pass

    # other platforms
    try:
        import psutil
        return psutil.virtual_memory().total
    except (ImportError, AttributeError):
        pass

    return 0


def memory_used():
    """Returns the memory used in MBs. Calculated differently depending
    on the platform and designed for informational purposes only.

    """
    if sys.platform == 'linux2':
        pid = os.getpid()
        statm = '/proc/%d/statm' % pid

        with open(statm, 'r') as fp:
            try:
                rss_pages = float(fp.read().split()[1])
                memory_bytes = rss_pages * resource.getpagesize()

                return memory_bytes / (1024*1024)
            except Exception as _:
                pass
    return 0


def cpu_info():
    """calculate the cpu information
    :return:(cpu_vendor, cpu_model, cpu_mhz)
    """
    cpu_file = "/proc/cpuinfo"
    ret = ["unknown", "unknown", "unknown"]

    try:
        infos = {}
        with open(cpu_file, 'r') as f:
            for line in f:
                kv = line.split(":")
                if len(kv) != 2:
                    continue

                key = kv[0].strip()
                value = kv[1].strip()
                if key in infos:
                    break

                infos[key] = value

        ret[0] = infos['vendor_id']
        ret[1] = infos['model name']
        ret[2] = infos['cpu MHz']
    except Exception as _:
        pass

    return ret