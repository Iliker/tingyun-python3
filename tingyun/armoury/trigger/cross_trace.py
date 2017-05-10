# -*- coding: utf-8 -*-

"""this module is used to process the cross application/transaction trace with processing the header.
"""

import logging
import json


console = logging.getLogger(__name__)


def process_header(tracker, headers):
    """
    :param tracker:
    :param headers:
    :return:
    """
    action_trace_invoke = 0
    if not tracker.enabled:
        return

    if not tracker.call_tingyun_id:
        return

    tingyun_ids = tracker._tingyun_id.split("|")
    if len(tingyun_ids) < 2:
        console.debug("tingyun id is not satisfied, if this continue please contact us.")
        return

    # 1 current trace overflow the action threshold
    # 2 the called service has the overflow the action threshold.
    if (tracker.duration >= tracker.settings.action_tracer.action_threshold) or \
       (tracker._called_traced_data and hasattr(tracker._called_traced_data, "tr")):
        action_trace_invoke = 1

    services = {'ex': tracker.external_time, 'rds': tracker.redis_time, 'mc': tracker.memcache_time,
                'mon': tracker.mongo_time, 'db': tracker.db_time}

    duration = tracker.duration
    code_time = duration - sum([t for t in services.values() if t >= 0])
    trace_data = {
        "id": tingyun_ids[1],
        "action": tracker.path,
        "trId": tracker.generate_trace_guid(),
        "time":
            {
            'duration': duration,
            'qu': tracker.queque_time,
            'code': code_time,
        }
    }

    for key, value in services.items():
        if value >= 0:
            trace_data["time"][key] = value

    trace_data["tr"] = action_trace_invoke
    tracker.call_tingyun_id = ''  # 最后清空被跨应用数据，防止在自己的慢应用中多次上传
    headers.append(("X-Tingyun-Tx-Data", json.dumps(trace_data)))
