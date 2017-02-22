"""Host operations"""

import json
from . import shutdown, service, api, http_util


def get_available_port(stack_svc, host_id, start, end):
    """Get available port. Scans host and gets available port from given range"""
    service_id = None
    if stack_svc is not None:
        service_id = service.parse_service_id(stack_svc, True)

    ports = __get_host_ports(host_id)
    available_range = range(start, end + 1)
    for port in ports:
        if port['port'] in available_range:
            if port['serviceId'] == service_id:
                return port['port']
            available_range.remove(port['port'])

    if len(available_range) > 0:
        return available_range[0]
    shutdown.err('There is no available ports')

def __get(host_id):
    end_point = '{}/hosts/{}'.format(api.V1, host_id)
    response = http_util.get(end_point)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)

    return json.loads(response.text)

def __get_host_ports(host_id):
    data = __get(host_id)
    public_endpoints = data['publicEndpoints']
    ports = []
    for endpoint in public_endpoints:
        ports.append(endpoint['port'])
    return public_endpoints

def get_host_ip(host_id):
    """Gets host ip by its id"""

    end_point = '{}/hosts/{}'.format(api.V1, host_id)
    response = http_util.get(end_point)
    if response.status_code not in range(200, 300):
        shutdown.err(response.text)

    data = json.loads(response.text)
    if data['publicEndpoints']:
        return data['publicEndpoints'][0]['ipAddress']
    else:
        shutdown.err('There is no public endpoints on host ' + host_id)
