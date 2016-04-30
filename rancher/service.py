import json

import requests

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

        stack_id = Stack(self.config).get_stack_id(stack_name)
        service_id = self.__get_service_id(stack_id, service_name)

        return service_id
