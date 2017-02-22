"""Service operations"""

import json
from time import sleep, time
from . import stack, shutdown, api, http_util, config

def __get_service_id(stack_id, name, no_error=False):
    end_point = '{}/environments/{}/services'.format(api.V1, stack_id)
    response = http_util.get(end_point)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)

    data = json.loads(response.text)['data']
    for service in data:
        if 'name' in service and service['name'] == name:
            return service['id']
    if not no_error:
        shutdown.err('No such service ' + name)
    else:
        return None

def get_service_instances(service_id):
    """Get service instances"""

    end_point = '{}/services/{}/instances'.format(api.V1, service_id)
    response = http_util.get(end_point)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)
    instances = json.loads(response.text)['data']
    if not instances:
        shutdown.err('No instances for service ' + service_id)
    return instances

def parse_service_id(host_name, no_error=False):
    """Parse service id"""
    host_tokens = host_name.split('.')
    stack_name = host_tokens[1]
    service_name = host_tokens[0]
    stack_id = stack.get_stack_id(stack_name, no_error)
    if stack_id is None:
        return None
    service_id = __get_service_id(stack_id, service_name)
    if service_id is None:
        return None
    else:
        return service_id

def upgrade(host_name, data=None):
    """Upgrade service"""
    service_id = parse_service_id(host_name)
    __init_upgrade(service_id, data)
    __wait_for_upgrade(service_id)
    __wait_for_healthy(service_id)
    __finish_upgrade(service_id)

def __init_upgrade(service_id, data):
    payload = __get(service_id)
    if data is not None:
        payload.update(data)
    end_point = '{}/services/{}/?action=upgrade'.format(api.V1, service_id)
    response = http_util.post(end_point, data)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)

def __finish_upgrade(service_id):
    end_point = '{}services/{}/?action=finishupgrade'.format(
        api.V1, service_id)
    response = http_util.post(end_point, {})
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)

def __wait_for_upgrade(service_id):
    timeout = 360
    stop_time = int(time()) + timeout
    state = None
    while int(time()) <= stop_time:
        state = __get_state(service_id)
        if state == 'upgraded':
            return
        sleep(5)
    shutdown.err(
        'Timeout while waiting to service upgrade. Current state is: ' + state)

def __wait_for_healthy(service_id):
    timeout = 360
    stop_time = int(time()) + timeout
    health_state = None
    while int(time()) <= stop_time:
        health_state = __get_health_state(service_id)
        if health_state == 'healthy':
            return
        sleep(5)
    shutdown.err(
        'Timeout while waiting to service become healthy. Current health state is: '
        + health_state)

def __get(service_id):
    end_point = '{}/services/{}'.format(api.V1, service_id)
    response = http_util.get(end_point)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)
    return json.loads(response.text)

def __get_lb_service(service_id):
    end_point = '{}/loadbalancerservices/{}'.format(
        api.V2_BETA, service_id)
    response = http_util.get(end_point)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)
    return json.loads(response.text)

def __get_state(service_id):
    service = __get(service_id)
    return service['state']

def __get_health_state(service_id):
    service = __get(service_id)
    return service['healthState']

def update_load_balancer_service(service_id, data):
    """Update load balancer target"""

    lb_config = __get_lb_service(service_id)
    payload = merge(lb_config, data)
    end_point = '{}/projects/{}/loadbalancerservices/{}'.format(
        api.V2_BETA, config.RANCHER_PROJECT_ID, service_id)
    response = http_util.put(end_point, payload)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)

def merge(left, right, path=None):
    """Merge dicts"""

    if path is None:
        path = []
    for key in right:
        if key in left:
            if isinstance(left[key], dict) and isinstance(right[key], dict):
                merge(left[key], right[key], path + [str(key)])
            elif left[key] == right[key]:
                pass  # same leaf value
            elif isinstance(left[key], list) and isinstance(right[key], list):
                for item in right[key]:
                    if item not in left[key]:
                        left[key].append(item)
            else:
                raise Exception('Conflict at %s' %
                                '.'.join(path + [str(key)]))
        else:
            left[key] = right[key]
    return left
