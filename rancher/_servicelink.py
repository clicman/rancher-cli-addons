"""Manage service links"""

import json
import re
from rancher import shutdown, http_util, API, config


class ServiceLink(object):
    """Manage service links"""

    def __get_load_balancer_targets(self):
        services = self.get_load_balancer_services()
        service_ids = []
        for svc in services:
            service_ids.append(svc['id'])

        end_point = '{}/serviceconsumemaps?limit=-1'.format(API.V1)
        response = http_util.get(end_point)
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)

        data = json.loads(response.text)['data']
        services = []
        for item in data:
            if item['consumedServiceId'] in service_ids \
                    and 'ports' in item and item['ports'] is not None:
                services.append(
                    {'serviceId': item['consumedServiceId'],
                     'ports': item['ports'], 'state': item['state']})
        return services

    def __get_load_balancer_ports(self, lb_svc_id):
        end_point = '{}/loadbalancerservices/{}'.format(API.V1, lb_svc_id)
        response = http_util.get(end_point)
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)

        data = json.loads(response.text)
        return data['lbConfig']['portRules']

    def __set_load_balancer_targets(self, targets):
        payload = {'serviceLinks': targets}
        end_point = '{}/loadbalancerservices/{}/?action=setservicelinks'.format(
            API.V1, config.LOAD_BALANCER_SVC_ID)
        response = http_util.post(end_point, payload)
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)

    def add_load_balancer_target(self, svc_id, host, desired_port, internal_port):
        """Add load balancer port"""

        port_set = False
        targets = self.__get_load_balancer_targets()
        tcp_ports = self.__get_load_balancer_ports(svc_id)

        for idx, target in reversed(list(enumerate(targets))):
            if target['state'] == 'removed':
                del targets[idx]
                continue
            if target['serviceId'] == str(svc_id) and 'ports' in target:
                for port in target['ports']:
                    if port.lower().startswith(host.lower() + ':' + str(desired_port)) \
                            or (port.endswith('=' + str(internal_port)) and
                                    re.compile("^\\d+=\\d+$").match(port) is not None):
                        shutdown.info(
                            'This target already exists: ' + str(target))

                if str(desired_port) + ':' + str(desired_port) + '/tcp' in tcp_ports:
                    target['ports'].append(
                        str(desired_port) + '=' + str(internal_port))
                else:
                    target['ports'].append(
                        host + ':' + str(desired_port) + '=' + str(internal_port))

                port_set = True
                targets[idx] = target
        if not port_set:
            if str(desired_port) + ':' + str(desired_port) + '/tcp' in tcp_ports:
                targets.append(
                    {'serviceId': str(svc_id),
                     'ports': [str(desired_port) + '=' + str(internal_port)]})
            else:
                targets.append(
                    {'serviceId': str(svc_id),
                     'ports': [host + ':' + str(desired_port) + '=' + str(internal_port)]})
        self.__set_load_balancer_targets(targets)
        self.__update_load_balancer_service()

    def remove_load_balancer_target(self, svc_id, host, desired_port):
        """Remove load balancer target"""

        port_removed = False
        targets = self.__get_load_balancer_targets()
        for idx, target in reversed(list(enumerate(targets))):
            if target['state'] == 'removed':
                del targets[idx]
                continue
            if target['serviceId'] == str(svc_id) and 'ports' in target:
                for port in target['ports']:
                    if port.lower().startswith(host.lower() + ':' + str(desired_port)) \
                            or (port.startswith(str(desired_port) + '=')
                                    and re.compile("^\\d+=\\d+$").match(port) is not None):
                        target['ports'].remove(port)
                        port_removed = True
                        if len(target['ports']) > 0:
                            targets[idx] = target
                        else:
                            del targets[idx]
                            # Commented break. It because rancher can create duplicate ports.
                            # https://github.com/rancher/rancher/issues/4631
                            # break
                            # if port_removed:
                            # break
        if not port_removed:
            shutdown.info('No such target')
        self.__set_load_balancer_targets(targets)
        self.__update_load_balancer_service()

    def __update_load_balancer_service(self):
        end_point = '{}/loadbalancerservices/{}/?action=update'.format(
            API.V1, config.LOAD_BALANCER_SVC_ID)
        response = http_util.post(end_point, {})
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)

    def get_available_port(self, lb_svc_id, ports_start, ports_end, svc_id=None):
        """Get available port"""

        available_range = range(ports_start, ports_end + 1)
        ports = self.__get_load_balancer_ports(lb_svc_id)
        for port in ports:
            if port['protocol'] == 'tcp' and port['sourcePort'] in available_range:
                if port['serviceId'] == svc_id:
                    return port['sourcePort']
                available_range.remove(port['sourcePort'])
        if len(available_range) > 0:
            return available_range[0]
        shutdown.err('There is no available ports')

    def get_service_port(self, service_id):
        """Get service port"""

        targets = self.__get_load_balancer_targets()
        for target in targets:
            if target['serviceId'] == str(service_id) and 'ports' in target:
                port = target['ports'][0]
                if ':' in port:
                    return port.split(':')[1].split('=')[0]
                else:
                    return port.split('=')[0]
        return -1

    def get_load_balancer_services(self):
        """Get LB service"""

        end_point = '{}/loadbalancerservices/{}/consumedservices'.format(
            API.V1, config.LOAD_BALANCER_SVC_ID)
        response = http_util.get(end_point)
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)

        data = json.loads(response.text)
        return data['data']
