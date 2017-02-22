#!/usr/bin/python

import argparse
import json
import os

from rancher import ServiceLink, Service, Stack, Host, config


def main():
    parser = argparse.ArgumentParser(
        description='Rancher command line client to add/remove load balancer rules.')
    # Environment params
    parser.add_argument('--apiUrl', default=os.environ.get('RANCHER_API_URL'),
                        help='api base url, $RANCHER_API_URL environment variable can be used')
    parser.add_argument('--apiKey', default=os.environ.get('RANCHER_API_KEY'),
                        help='api key, $RANCHER_API_KEY environment variable can be used')
    parser.add_argument('--apiSecret', default=os.environ.get('RANCHER_API_SECRET'),
                        help='api secret, $RANCHER_API_SECRET environment variable can be used')
    parser.add_argument('--projectId', default=os.environ.get('RANCHER_PROJECT_ID'),
                        help='project environment, $RANCHER_PROJECT_ID environment variable can be used')
    parser.add_argument('--loadBalancerId', default=os.environ.get('RANCHER_LB_ID'),
                        help='load balancer service id, $RANCHER_LB_ID environment variable can be used')

    parser.add_argument('--stackName',
                        help='Stack name')
    parser.add_argument('--stackTags',
                        help='Comma separated stack tags (optional)', default=None)

    parser.add_argument('--stackUpgradeTimeout', default=os.environ.get('STACK_UPGRADE_TIMEOUT', 360),
                        help='timeout for stack upgrade in seconds. Default 360')
    parser.add_argument('--stackActiveTimeout', default=os.environ.get('STACK_ACTIVE_TIMEOUT', 360),
                        help='timeout for stack become active in seconds. Default 360')
    parser.add_argument('--stackHealthyTimeout', default=os.environ.get('STACK_HEALTHY_TIMEOUT', 360),
                        help='timeout for stack become healthy in seconds. Default 360')

    parser.add_argument('--dockerCompose',
                        help='docker compose path')
    parser.add_argument('--rancherCompose',
                        help='Rancher compose path (optional)', default=None)
    parser.add_argument('--stackEnvironment', default='{}',
                        help='Stack environment variables json')
    parser.add_argument('--stackSvc', default=None,
                        help='Stack/Service string')
    # Action params
    required_named = parser.add_argument_group('required arguments')
    required_named.add_argument('--action',
                                help='add-link,  remove-lnk, create-stack, remove-stack, get-port, get-service-port, upgrade-service, get-container-id, get-host-ip')
    parser.add_argument('--serviceId',
                        help="""target service id. Optional, parsed from hostname if not
                        set by pattern: serviceName.stackName.somedomain.TLD""")
    parser.add_argument('--host', help='target hostname')
    parser.add_argument(
        '--hostId', help='Host id where to find available port')
    parser.add_argument('--portRangeStart', help='Start of desired port range')
    parser.add_argument('--portRangeEnd', help='End of desired port range')
    parser.add_argument(
        '--externalPort', help='external service port', type=int)
    parser.add_argument('--internalPort', default=None, type=int,
                        help='internal service port. Optional, not needed for remove action')
    parser.add_argument('--data', default=None, type=str,
                        help='Data payload. Optional')
    args = parser.parse_args()
    var_args = vars(args)

    internal_port = var_args.pop('internalPort')
    service_id = var_args.pop('serviceId')

    if args.action is None:
        parser.parse_args(['-h'])
        exit(2)

    config.RANCHER_BASE_URL = args.apiUrl
    config.RANCHER_API_ACCESS_KEY = args.apiKey
    config.RANCHER_API_SECRET_KEY = args.apiSecret
    config.RANCHER_PROJECT_ID = args.projectId
    config.LOAD_BALANCER_SVC_ID = args.loadBalancerId
    config.STACK_UPGRADE_TIMEOUT = args.stackUpgradeTimeout
    config.STACK_ACTIVE_TIMEOUT = args.stackActiveTimeout
    config.STACK_HEALTHY_TIMEOUT = args.stackHealthyTimeout

    if service_id is None and args.host is not None:
        service_id = Service(config).parse_service_id(args.host, True)

    if args.action.lower() not in ['add-link', 'remove-link', 'create-stack',
                                   'remove-stack', 'get-port',
                                   'get-service-port', 'update-lb',
                                   'get-svc-id', 'get-container-id', 'get-host-ip']:
        parser.parse_args(['-h'])
        exit(2)

    # actions
    if args.action.lower() == 'get-port':
        print ServiceLink().get_available_port(args.loadBalancerId,
                                               int(args.portRangeStart),
                                               int(args.portRangeEnd), service_id)

    elif args.action.lower() == 'get-service-port':
        print ServiceLink().get_service_port(service_id)

    elif args.action.lower() == 'add-link':
        ServiceLink().add_load_balancer_target(service_id, args.host, args.externalPort,
                                               internal_port)
    elif args.action.lower() == 'remove-link':
        ServiceLink().remove_load_balancer_target(
            service_id, args.host, args.externalPort)

    elif args.action.lower() == 'create-stack':
        Stack().create(args.stackName, args.dockerCompose,
                       args.rancherCompose, args.stackTags)

    elif args.action.lower() == 'remove-stack':
        Stack().remove('name', args.stackName)

    elif args.action.lower() == 'update-lb':
        Service().update_load_balancer_service(
            args.loadBalancerId, json.loads(args.data))

    elif args.action.lower() == 'get-svc-id':
        print Service().parse_service_id(args.host)

    elif args.action.lower() == 'get-container-id':
        instances = Service().get_service_instances(service_id)
        print instances[0]['externalId']

    elif args.action.lower() == 'get-host-ip':
        instances = Service().get_service_instances(service_id)
        host_id = instances[0]['hostId']
        print Host().get_host_ip(host_id)

main()
