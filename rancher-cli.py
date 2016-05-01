import argparse
import os

from rancher import servicelink, service, stack


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
    parser.add_argument('--stackName',
                        help='Stack name')
    parser.add_argument('--dockerCompose',
                        help='docker compose path')
    parser.add_argument('--rancherCompose',
                        help='Rancher compose path')
    # Action params
    required_named = parser.add_argument_group('required arguments')
    required_named.add_argument('--action', help='add-link,  remove-lnk, create-stack, remove-stack')
    parser.add_argument('--serviceId',
                        help="""target service id. Optional, parsed from hostname if not
                        set by pattern: serviceName.stackName.somedomain.TLD""")
    parser.add_argument('--host', help='target hostname')
    parser.add_argument('--externalPort', help='external service port', type=int)
    parser.add_argument('--internalPort', default=None, type=int,
                        help='internal service port. Optional, not needed for remove action')
    args = parser.parse_args()
    var_args = vars(args)

    internal_port = var_args.pop('internalPort')
    service_id = var_args.pop('serviceId')

    # if None in var_args.values():
    #     parser.parse_args(['-h'])
    #     exit(2)

    config = {'rancherBaseUrl': args.apiUrl,
              'rancherApiAccessKey': args.apiKey,
              'rancherApiSecretKey': args.apiSecret,
              'loadBalancerSvcId': args.loadBalancerId
              }

    if service_id is None and args.host is not None:
        service_id = service.Service(config).parse_service_id(args.host)

    if args.action.lower() not in ['add-link', 'remove-link', 'create-stack', 'remove-stack']:
        parser.parse_args(['-h'])
        exit(2)
    if args.action.lower() == 'add' and internal_port is None:
        parser.parse_args(['-h'])
        exit(2)

    if args.action.lower() == 'add-link':
        servicelink.ServiceLink(config).add_load_balancer_target(service_id, args.host, args.externalPort,
                                                                 internal_port)
    elif args.action.lower() == 'remove-link':
        servicelink.ServiceLink(config).remove_load_balancer_target(service_id, args.host, args.externalPort)

    elif args.action.lower() == 'create-stack':
        stack.Stack(config).create(args.stackName, args.dockerCompose, args.rancherCompose)

    elif args.action.lower() == 'remove-stack':
        stack.Stack(config).remove('name', args.stackName)


main()
