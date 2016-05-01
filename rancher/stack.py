import json
from rancher import exit, util
import requests
import yaml


class Stack:
    rancherApiVersion = '/v1/'
    request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def __init__(self, configuration):
        self.config = configuration

    def get_stack_id(self, name):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'environments?limit=-1'
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)

        if response.status_code not in range(200, 300):
            exit.err(response.text)

        data = json.loads(response.text)['data']
        for environment in data:
            if 'name' in environment and environment['name'] == name:
                return environment['id']

        exit.err('No such stack ' + name)

    def remove(self, value_type, value):
        payload = '{}'
        if value_type == 'name':
            stack_id = self.get_stack_id(value)
        elif value_type == 'id':
            stack_id = value
        else:
            exit.err('Type must me one of name or id')

        end_point = self.config[
                        'rancherBaseUrl'] + self.rancherApiVersion + 'environments/' + stack_id + '/?action=remove'
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def create(self, name, docker_compose_path, rancher_compose_path):
        try:
            with open(docker_compose_path) as file_object:
                docker_compose = file_object.read()
        except IOError, e:
            exit.err(e.strerror + ': ' + docker_compose_path)

        try:
            with open(rancher_compose_path) as file_object:
                rancher_compose = file_object.read()
        except IOError, e:
            exit.err(e.strerror + ': ' + rancher_compose_path)

        stack_data = {'type': 'environment',
                      'startOnCreate': True,
                      'name': name,
                      'dockerCompose': docker_compose,
                      'rancherCompose': rancher_compose}
        payload = util.build_payload(stack_data)

        end_point = self.config[
                        'rancherBaseUrl'] + self.rancherApiVersion + 'environment'
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
