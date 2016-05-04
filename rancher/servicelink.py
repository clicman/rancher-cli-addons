import json

import re

from rancher import exit, util
import requests


class ServiceLink:
    rancherApiVersion = '/v1/'
    request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def __init__(self, configuration):
        self.config = configuration

    def __get_load_balancer_targets(self):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'serviceconsumemaps?limit=-1'
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

        data = json.loads(response.text)['data']
        services = []
        for item in data:
            if 'ports' in item:
                if item['ports'] is not None:
                    services.append(
                        {'serviceId': item['consumedServiceId'], 'ports': item['ports'], 'state': item['state']})
        return services

    def __get_load_balancer_ports(self):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'loadbalancerservices/' + self.config[
            'loadBalancerSvcId']
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

        data = json.loads(response.text)
        return data['launchConfig']['ports']

    def __set_load_balancer_targets(self, targets):
        payload = util.build_payload({'serviceLinks': targets})
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'loadbalancerservices/' + self.config[
            'loadBalancerSvcId'] + \
                    '/?action=setservicelinks'
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def add_load_balancer_target(self, svc_id, host, desired_port, internal_port):
        port_set = False
        targets = self.__get_load_balancer_targets()
        for idx, target in reversed(list(enumerate(targets))):
            if target['state'] == 'removed':
                del targets[idx]
                continue
            if target['serviceId'] == str(svc_id) and 'ports' in target:
                for port in target['ports']:
                    if port.lower().startswith(host.lower() + ':' + str(desired_port)):
                        exit.info('This target already exists: ' + str(target))
                target['ports'].append(host + ':' + str(desired_port) + '=' + str(internal_port))
                port_set = True
                targets[idx] = target
        if not port_set:
            targets.append(
                {'serviceId': str(svc_id), 'ports': [host + ':' + str(desired_port) + '=' + str(internal_port)]})
        self.__set_load_balancer_targets(targets)
        self.__update_load_balancer_service()

    def remove_load_balancer_target(self, svc_id, host, desired_port):
        port_removed = False
        targets = self.__get_load_balancer_targets()
        for idx, target in reversed(list(enumerate(targets))):
            if target['state'] == 'removed':
                del targets[idx]
                continue
            if target['serviceId'] == str(svc_id) and 'ports' in target:
                for port in target['ports']:
                    if port.lower().startswith(host.lower() + ':' + str(desired_port)):
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
            exit.info('No such target')
        self.__set_load_balancer_targets(targets)
        self.__update_load_balancer_service()

    def __update_load_balancer_service(self):
        payload = '{}'
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'loadbalancerservices/' + self.config[
            'loadBalancerSvcId'] + \
                    '/?action=update'
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def get_available_port(self):
        ports = self.__get_load_balancer_ports()
        port_list = []
        for port in ports:
            if '/tcp' in port:
                port_list.append(port.split(':')[0])
        targets = self.__get_load_balancer_targets()
        for target in targets:
            if 'ports' in target:
                for port in target['ports']:
                    if re.compile("^\d+=\d+$").match(port) is not None:
                        port_list.remove(port.split('=')[0])
        if len(port_list) > 0:
            return port_list[0]
        print 'There is no available ports'
        exit(2)
