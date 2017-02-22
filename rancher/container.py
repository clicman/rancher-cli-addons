""" Manages containers """

import json
from . import http_util, shutdown, api


def __get(instance_id):
    end_point = '{}/containers/{}'.format(api.V2_BETA, instance_id)

    response = http_util.get(end_point)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)
    return json.loads(response.text)


def get_host_id(instance_id):
    """Get host id by instance id"""
    return __get(instance_id)['hostId']


def get_container_id(instance_id):
    """Get container id by instance id"""
    return __get(instance_id)['externalId']
