import json
import requests
import argparse
import os

rancherApiVersion = '/v1/'

config = {}
request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}


def main():
    parser = argparse.ArgumentParser(description='Rancher command line client to add/remove load balancer rules.')
    # Environment params
    parser.add_argument('--apiUrl', default=os.environ.get('RANCHER_API_URL'),
                        help='api base url, $RANCHER_API_URL environment variable can be used')
    parser.add_argument('--apiKey', default=os.environ.get('RANCHER_API_KEY'),
                        help='api key, $RANCHER_API_KEY environment variable can be used')
    parser.add_argument('--apiSecret', default=os.environ.get('RANCHER_API_SECRET'),
                        help='api secret, $RANCHER_API_SECRET environment variable can be used')
    parser.add_argument('--loadBalancerId', default=os.environ.get('RANCHER_LB_ID'),
                        help='load balancer service id, $RANCHER_LB_ID environment variable can be used')

    # Action params
    required_named = parser.add_argument_group('required arguments')
    required_named.add_argument('--action', help='add or remove')
    parser.add_argument('--serviceId',
                        help='target service id. Optional, parsed from hostname if not set by pattern: serviceName.stackName.somedomain.TLD')
    required_named.add_argument('--host', help='target hostname')
    required_named.add_argument('--externalPort', help='external service port', type=int)
    parser.add_argument('--internalPort', default=None, type=int,
                        help='internal service port. Optional, not needed for remove action')
    args = parser.parse_args()
    var_args = vars(args)

    internal_port = var_args.pop('internalPort')
    service_id = var_args.pop('serviceId')

    if None in var_args.values():
        parser.parse_args(['-h'])
        exit(2)

    config['rancherBaseUrl'] = args.apiUrl
    config['rancherApiAccessKey'] = args.apiKey
    config['rancherApiSecretKey'] = args.apiSecret
    config['loadBalancerSvcId'] = args.loadBalancerId

    if service_id is None:
        service_id = parse_service_id(args.host)

    if args.action.lower() not in ['add', 'remove']:
        parser.parse_args(['-h'])
        exit(2)
    if args.action.lower() == 'add' and internal_port is None:
        parser.parse_args(['-h'])
        exit(2)

    if args.action.lower() == 'add':
        add_load_balancer_target(service_id, args.host, args.externalPort, internal_port)
    else:
        remove_load_balancer_target(service_id, args.host, args.externalPort)
    update_load_balancer_service()


def get_load_balancer_targets():
    end_point = config['rancherBaseUrl'] + rancherApiVersion + 'serviceconsumemaps?limit=-1'
    response = requests.get(end_point, auth=(config['rancherApiAccessKey'], config['rancherApiSecretKey']),
                            headers=request_headers, verify=False)
    if response.status_code != 200:
        err(response.text)

    data = json.loads(response.text)['data']
    services = []
    for item in data:
        if 'ports' in item:
            if item['ports'] is not None:
                services.append({'serviceId': item['consumedServiceId'], 'ports': item['ports']})
    return services


def set_loadbalancer_targets(targets):
    payload = build_payload(targets)
    end_point = config['rancherBaseUrl'] + rancherApiVersion + 'loadbalancerservices/' + config['loadBalancerSvcId'] + \
                '/?action=setservicelinks'
    response = requests.post(end_point, auth=(config['rancherApiAccessKey'], config['rancherApiSecretKey']),
                             headers=request_headers, verify=False, data=payload)
    if response.status_code != 200:
        err(response.text)


def add_load_balancer_target(svc_id, host, desired_port, internal_port):
    port_set = False
    targets = get_load_balancer_targets()
    for idx, target in enumerate(targets):
        if target['serviceId'] == str(svc_id) and 'ports' in target:
            for port in target['ports']:
                if port.lower().startswith(host.lower() + ':' + str(desired_port)):
                    err('This target already exists: ' + str(target))
            target['ports'].append(host + ':' + str(desired_port) + '=' + str(internal_port))
            port_set = True
            targets[idx] = target
    if not port_set:
        targets.append({'serviceId': str(svc_id), 'ports': [host + ':' + str(desired_port) + '=' + str(internal_port)]})
    set_loadbalancer_targets(targets)


def remove_load_balancer_target(svc_id, host, desired_port):
    port_removed = False
    targets = get_load_balancer_targets()
    for idx, target in enumerate(targets):
        if target['serviceId'] == str(svc_id) and 'ports' in target:
            for port in target['ports']:
                if port.lower().startswith(host.lower() + ':' + str(desired_port)):
                    target['ports'].remove(port)
                    port_removed = True
                    if len(target['ports']) > 0:
                        targets[idx] = target
                    else:
                        del targets[idx]
                    break
        if port_removed:
            break
    if not port_removed:
        info('No such target')
    set_loadbalancer_targets(targets)


def build_payload(targets):
    targets = {'serviceLinks': targets}
    payload = json.dumps(targets)
    return payload


def get_stack_id(name):
    end_point = config['rancherBaseUrl'] + rancherApiVersion + 'environments?limit=-1'
    response = requests.get(end_point, auth=(config['rancherApiAccessKey'], config['rancherApiSecretKey']),
                            headers=request_headers, verify=False)

    if response.status_code != 200:
        err(response.text)

    data = json.loads(response.text)['data']
    for environment in data:
        if 'name' in environment and environment['name'] == name:
            return environment['id']

    err('No such stack ' + name)


def get_service_id(stack_id, name):
    end_point = config['rancherBaseUrl'] + rancherApiVersion + 'environments/' + stack_id + '/services'
    response = requests.get(end_point, auth=(config['rancherApiAccessKey'], config['rancherApiSecretKey']),
                            headers=request_headers, verify=False)

    if response.status_code != 200:
        err(response.text)

    data = json.loads(response.text)['data']
    for service in data:
        if 'name' in service:
            return service['id']

    err('No such service ' + name)


def parse_service_id(host_name):
    host_tokens = host_name.split('.')
    stack_name = host_tokens[1]
    service_name = host_tokens[0]
    stack_id = get_stack_id(stack_name)
    service_id = get_service_id(stack_id, service_name)

    return service_id


def update_load_balancer_service():
    payload = '{}'
    end_point = config['rancherBaseUrl'] + rancherApiVersion + 'loadbalancerservices/' + config['loadBalancerSvcId'] + \
                '/?action=update'
    response = requests.post(end_point, auth=(config['rancherApiAccessKey'], config['rancherApiSecretKey']),
                             headers=request_headers, verify=False, data=payload)
    if response.status_code not in range(200, 300):
        err(response.text)


def err(text):
    print('Error: ' + text)
    exit(2)


def info(text):
    print(text)
    exit(0)


main()
