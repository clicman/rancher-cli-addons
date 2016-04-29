import json
import exit

import requests


class ServiceLinks:
    rancherApiVersion = '/v1/'
    request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def __init__(self, configuration):
        self.config = configuration

    def get_load_balancer_targets(self):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'serviceconsumemaps?limit=-1'
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code != 200:
            exit.err(response.text)

        data = json.loads(response.text)['data']
        services = []
        for item in data:
            if 'ports' in item:
                if item['ports'] is not None:
                    services.append({'serviceId': item['consumedServiceId'], 'ports': item['ports']})
        return services

    def set_loadbalancer_targets(self, targets):
        payload = self.build_payload(targets)
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'loadbalancerservices/' + self.config[
            'loadBalancerSvcId'] + \
                    '/?action=setservicelinks'
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code != 200:
            exit.err(response.text)

    def add_load_balancer_target(self, svc_id, host, desired_port, internal_port):
        port_set = False
        targets = self.get_load_balancer_targets()
        for idx, target in enumerate(targets):
            if target['serviceId'] == str(svc_id) and 'ports' in target:
                for port in target['ports']:
                    if port.lower().startswith(host.lower() + ':' + str(desired_port)):
                        exit.err('This target already exists: ' + str(target))
                target['ports'].append(host + ':' + str(desired_port) + '=' + str(internal_port))
                port_set = True
                targets[idx] = target
        if not port_set:
            targets.append(
                {'serviceId': str(svc_id), 'ports': [host + ':' + str(desired_port) + '=' + str(internal_port)]})
        self.set_loadbalancer_targets(targets)

    def remove_load_balancer_target(self, svc_id, host, desired_port):
        port_removed = False
        targets = self.get_load_balancer_targets()
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
            exit.info('No such target')
        self.set_loadbalancer_targets(targets)

    @staticmethod
    def build_payload(targets):
        targets = {'serviceLinks': targets}
        payload = json.dumps(targets)
        return payload

    def get_stack_id(self, name):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'environments?limit=-1'
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)

        if response.status_code != 200:
            exit.err(response.text)

        data = json.loads(response.text)['data']
        for environment in data:
            if 'name' in environment and environment['name'] == name:
                return environment['id']

        exit.err('No such stack ' + name)

    def get_service_id(self, stack_id, name):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'environments/' + stack_id + '/services'
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)

        if response.status_code != 200:
            exit.err(response.text)

        data = json.loads(response.text)['data']
        for service in data:
            if 'name' in service:
                return service['id']

        exit.err('No such service ' + name)

    def parse_service_id(self, host_name):
        host_tokens = host_name.split('.')
        stack_name = host_tokens[1]
        service_name = host_tokens[0]
        stack_id = self.get_stack_id(stack_name)
        service_id = self.get_service_id(stack_id, service_name)

        return service_id

    def update_load_balancer_service(self):
        payload = '{}'
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'loadbalancerservices/' + self.config[
            'loadBalancerSvcId'] + \
                    '/?action=update'
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
