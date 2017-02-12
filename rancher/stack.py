import json
import requests
from time import sleep, time

from rancher import exit, util


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
        stack_id = None
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
            exit.err('Could not remove stack: {}'.format(response.text))

    def create(self, name, docker_compose_path, rancher_compose_path, environment=None):
        if environment is None:
            environment = {}
        print ('Creating stack ' + name + '...')
        docker_compose = self.__get_docker_compose(docker_compose_path)
        rancher_compose = self.__get_rancher_compose(rancher_compose_path)

        stack_data = {
            "type": "stack",
            "startOnCreate": True,
            "name": name,
            'dockerCompose': docker_compose,
            'rancherCompose': rancher_compose}
        payload = util.build_payload(stack_data)
        end_point = self.config['rancherBaseUrl'] + '/v2-beta/' + 'projects/' + self.config['rancherProjectId'] + '/stack'
        print(end_point)
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            if json.loads(response.text)['code'] == 'NotUnique':
                print ('Oops! Stack already exists. Let`s upgrade it...')
                self.upgrade(name, docker_compose_path, rancher_compose_path)
            else:
                exit.err(response.text)
        stack_id = self.get_stack_id(name)
        self.__wait_for_active(stack_id)
        self.__wait_for_healthy(stack_id)
        print ('Stack ' + name + ' created')

    def __init_upgrade(self, name, docker_compose_path, rancher_compose_path):
        print ('Initializing stack ' + name + ' upgrade...')
        docker_compose = self.__get_docker_compose(docker_compose_path)
        rancher_compose = self.__get_rancher_compose(rancher_compose_path)

        stack_data = {'type': 'environment',
                      'startOnCreate': True,
                      'name': name,
                      'dockerCompose': docker_compose,
                      'rancherCompose': rancher_compose}
        payload = util.build_payload(stack_data)

        end_point = self.config[
                        'rancherBaseUrl'] + self.rancherApiVersion + 'environments/' + self.get_stack_id(
            name) + '/?action=upgrade'
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
        print ('Stack upgrade initialized')

    def __finish_upgrade(self, stack_id):
        payload = '{}'
        end_point = '{}{}environments/{}/?action=finishupgrade'.format(
            self.config['rancherBaseUrl'], self.rancherApiVersion, stack_id)
        response = requests.post(end_point,
                                 auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                 headers=self.request_headers, verify=False, data=payload)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

    def __wait_for_upgrade(self, stack_id):
        print ('Let`s wait until stack upgraded...')
        timeout = self.config['stackUpgradeTimeout']
        stop_time = int(time()) + timeout
        state = None
        while int(time()) <= stop_time:
            state = self.__get_state(stack_id)
            if state == 'upgraded':
                print ('Stack ' + stack_id + ' upgraded')
                return
            sleep(5)
        exit.err('Timeout while waiting to service upgrade. Current state is: ' + state)

    def __wait_for_active(self, stack_id):
        print ('Let`s wait until stack become active...')
        timeout = self.config['stackActiveTimeout']
        stop_time = int(time()) + timeout
        state = None
        while int(time()) <= stop_time:
            state = self.__get_state(stack_id)
            if state == 'active':
                print ('Stack ' + stack_id + ' active')
                return
            sleep(5)
        exit.err('Timeout while waiting to service upgrade. Current state is: ' + state)

    def __wait_for_healthy(self, stack_id):
        print ('Let`s wait until stack become healthy...')
        timeout = self.config['stackHealthyTimeout']
        stop_time = int(time()) + timeout
        health_state = None
        while int(time()) <= stop_time:
            health_state = self.__get_health_state(stack_id)
            if health_state == 'healthy':
                print ('Stack ' + stack_id + ' is now healthy')
                return
            sleep(5)
        exit.err('Timeout while waiting to stack become healthy. Current health state is: ' + health_state)

    def __get(self, stack_id):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'environments/' + stack_id
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
        return json.loads(response.text)

    def __get_state(self, stack_id):
        service = self.__get(stack_id)
        return service['state']

    def __get_health_state(self, stack_id):
        service = self.__get(stack_id)
        return service['healthState']

    @staticmethod
    def __get_docker_compose(docker_compose_path):
        try:
            with open(docker_compose_path) as file_object:
                return file_object.read()
        except IOError, e:
            exit.err('Could not open docker-compose file: {}\n{}'.format(docker_compose_path, e.message))

    @staticmethod
    def __get_rancher_compose(rancher_compose_path):
        if rancher_compose_path is None:
            return ''
        else:
            try:
                with open(rancher_compose_path) as file_object:
                    return file_object.read()
            except IOError, e:
                exit.err('Could not open rancher-compose file: {}\n{}'.format(rancher_compose_path, e.message))

    def upgrade(self, name, docker_compose_path, rancher_compose_path):
        stack_id = self.get_stack_id(name)
        self.__init_upgrade(name, docker_compose_path, rancher_compose_path)
        self.__wait_for_upgrade(stack_id)
        self.__finish_upgrade(stack_id)
        self.__wait_for_healthy(stack_id)
