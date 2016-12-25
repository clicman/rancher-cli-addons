import json
import requests
from time import time, sleep
from rancher.stack import Stack
from rancher import exit


class Service:
    rancherApiVersion = '/v1/'
    request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def __init__(self, configuration):
        self.config = configuration

    def __get_service_id(self, stack_id, name):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'environments/' + stack_id + '/services'
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)

        if response.status_code not in range(200, 300):
            exit.err(response.text)

        data = json.loads(response.text)['data']
        for service in data:
            if 'name' in service and service['name'] == name:
                return service['id']

        exit.err('No such service ' + name)

    def get_service_instances(self, service_id):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'services/' + service_id + '/instances'
        response = requests.get(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False)         
        if response.status_code not in range(200, 300):
            exit.err(response.text)
        instances = json.loads(response.text)['data']
        if not instances:
            exit.err('No instances for service ' + service['name'])
        return instances

    def parse_service_id(self, host_name):
        host_tokens = host_name.split('.')
        stack_name = host_tokens[1]
        service_name = host_tokens[0]
        stack_id = Stack(self.config).get_stack_id(stack_name)
        service_id = self.__get_service_id(stack_id, service_name)

        return service_id

    def upgrade(self, host_name, data=None):
        service_id = self.parse_service_id(host_name)
        self.__init_upgrade(service_id, data)
        self.__wait_for_upgrade(service_id)
        self.__wait_for_healthy(service_id)
        self.__finish_upgrade(service_id)

    def __init_upgrade(self, service_id, data):
        payload = self.__get(service_id)
        if data is not None:
            payload.update(data)
        end_point = '{}{}services/{}/?action=upgrade'.format(
            self.config['rancherBaseUrl'], self.rancherApiVersion, service_id)
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=json.dumps(payload))
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def __finish_upgrade(self, service_id):
        payload = '{}'
        end_point = '{}{}services/{}/?action=finishupgrade'.format(
            self.config['rancherBaseUrl'], self.rancherApiVersion, service_id)
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def __wait_for_upgrade(self, service_id):
        timeout = 360
        stop_time = int(time()) + timeout
        state = None
        while int(time()) <= stop_time:
            state = self.__get_state(service_id)
            if state == 'upgraded':
                return
            sleep(5)
        exit.err('Timeout while waiting to service upgrade. Current state is: ' + state)

    def __wait_for_healthy(self, service_id):
        timeout = 360
        stop_time = int(time()) + timeout
        health_state = None
        while int(time()) <= stop_time:
            health_state = self.__get_health_state(service_id)
            if health_state == 'healthy':
                return
            sleep(5)
        exit.err('Timeout while waiting to service become healthy. Current health state is: ' + health_state)

    def __get(self, service_id):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'services/' + service_id
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
        return json.loads(response.text)

    def __get_lb_service(self, service_id):
        end_point = self.config['rancherBaseUrl'] + '/v2-beta/' + 'loadbalancerservices/' + service_id
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
        return json.loads(response.text)

    def __get_state(self, service_id):
        service = self.__get(service_id)
        return service['state']

    def __get_health_state(self, service_id):
        service = self.__get(service_id)
        return service['healthState']

    def update_load_balancer_service(self, service_id, data):
        lb_config = self.__get_lb_service(service_id)
        payload = self.merge(lb_config, data)
        end_point = '{}{}loadbalancerservices/{}'.format(
            self.config['rancherBaseUrl'], '/v2-beta/', service_id)
        response = requests.put(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False, data=json.dumps(payload))
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def merge(self, a, b, path=None):
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.merge(a[key], b[key], path + [str(key)])
                elif a[key] == b[key]:
                    pass  # same leaf value
                elif isinstance(a[key], list) and isinstance(b[key], list):
                    for item in b[key]:
                        if item not in a[key]:
                            a[key].append(item)
                else:
                    raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
            else:
                a[key] = b[key]
        return a
