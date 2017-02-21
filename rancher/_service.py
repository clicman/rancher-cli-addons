import json
from time import sleep, time
import requests
from rancher import Stack, exit, API


class Service(object):
    """Service operations"""
    request_headers = {'Content-Type': 'application/json',
                       'Accept': 'application/json'}

    def __init__(self, configuration):
        self.config = configuration

    def __get_service_id(self, stack_id, name, no_error=False):
        end_point = self.config['rancherBaseUrl'] + '/' + \
            API.V1 + '/environments/' + stack_id + '/services'
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config[
                                    'rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)

        if response.status_code not in range(200, 300):
            exit.err(response.text)

        data = json.loads(response.text)['data']
        for service in data:
            if 'name' in service and service['name'] == name:
                return service['id']
        if not no_error:
            exit.err('No such service ' + name)
        else:
            return None

    def get_service_instances(self, service_id):
        """Get service instances"""
        end_point = self.config[
            'rancherBaseUrl'] + '/' + API.V1 + '/services/' + service_id + '/instances'
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config[
                                    'rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
        instances = json.loads(response.text)['data']
        if not instances:
            exit.err('No instances for service ' + service_id)
        return instances

    def parse_service_id(self, host_name, no_error=False):
        """Parse service id"""
        host_tokens = host_name.split('.')
        stack_name = host_tokens[1]
        service_name = host_tokens[0]
        stack_id = Stack(self.config).get_stack_id(stack_name, no_error)
        if stack_id is None:
            return None
        service_id = self.__get_service_id(stack_id, service_name)
        if service_id is None:
            return None
        else:
            return service_id

    def upgrade(self, host_name, data=None):
        """Upgrade service"""
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
            self.config['rancherBaseUrl'], API.V1, service_id)
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'],
                                       self.config['rancherApiSecretKey']),
                                 headers=self.request_headers,
                                 verify=False,
                                 data=json.dumps(payload))
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def __finish_upgrade(self, service_id):
        payload = '{}'
        end_point = '{}{}services/{}/?action=finishupgrade'.format(
            self.config['rancherBaseUrl'], API.V1, service_id)
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'],
                                       self.config['rancherApiSecretKey']),
                                 headers=self.request_headers,
                                 verify=False,
                                 data=payload)
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
        exit.err(
            'Timeout while waiting to service upgrade. Current state is: ' + state)

    def __wait_for_healthy(self, service_id):
        timeout = 360
        stop_time = int(time()) + timeout
        health_state = None
        while int(time()) <= stop_time:
            health_state = self.__get_health_state(service_id)
            if health_state == 'healthy':
                return
            sleep(5)
        exit.err(
            'Timeout while waiting to service become healthy. Current health state is: '
            + health_state)

    def __get(self, service_id):
        end_point = self.config['rancherBaseUrl'] + '/'\
            + API.V1 + '/services/' + service_id
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'],
                                      self.config['rancherApiSecretKey']),
                                headers=self.request_headers,
                                verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
        return json.loads(response.text)

    def __get_lb_service(self, service_id):
        end_point = self.config['rancherBaseUrl'] + '/' +\
            API.V2_BETA + '/loadbalancerservices/' + service_id
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'],
                                      self.config['rancherApiSecretKey']),
                                headers=self.request_headers,
                                verify=False)
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
        """Update load balancer target"""
        lb_config = self.__get_lb_service(service_id)
        payload = self.merge(lb_config, data)
        end_point = '{}/{}/{}/{}/loadbalancerservices/{}'.format(
            self.config['rancherBaseUrl'],
            API.V2_BETA, 'projects', self.config['rancherProjectId'], service_id)
        response = requests.put(end_point,
                                auth=(self.config['rancherApiAccessKey'],
                                      self.config['rancherApiSecretKey']),
                                headers=self.request_headers,
                                verify=False,
                                data=json.dumps(payload))
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def merge(self, left, right, path=None):
        """Merge dicts"""
        if path is None:
            path = []
        for key in right:
            if key in left:
                if isinstance(left[key], dict) and isinstance(right[key], dict):
                    self.merge(left[key], right[key], path + [str(key)])
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
