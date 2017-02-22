"""Manage Stack"""

import json
from time import sleep, time
from rancher import shutdown, http_util, API, config


class Stack(object):
    """Manage Stack"""

    def get_stack_id(self, name, no_error=False):
        """Get stack id"""

        end_point = '{}/environments?limit=-1'.format(API.V1)
        response = http_util.get(end_point)

        if response.status_code not in range(200, 300):
            shutdown.err(response.text)

        data = json.loads(response.text)['data']
        for environment in data:
            if 'name' in environment and environment['name'] == name:
                return environment['id']

        if not no_error:
            shutdown.err('No such stack ' + name)
        return None

    def remove(self, value_type, value):
        """Remove stack"""

        stack_id = None
        if value_type == 'name':
            stack_id = self.get_stack_id(value)
        elif value_type == 'id':
            stack_id = value
        else:
            shutdown.err('Type must me one of name or id')

        end_point = '{}/environments/{}/?action=remove'.format(
            API.V1, stack_id)
        response = http_util.post(end_point, {})
        if response.status_code not in range(200, 300):
            shutdown.err('Could not remove stack: {}'.format(response.text))

    def create(self, name, docker_compose_path, rancher_compose_path, stack_tags=None):
        """Create stack"""

        print 'Creating stack ' + name + '...'
        docker_compose = self.__get_docker_compose(docker_compose_path)
        rancher_compose = self.__get_rancher_compose(rancher_compose_path)

        payload = {
            "type": "stack",
            "startOnCreate": True,
            "name": name,
            "group": stack_tags,
            'dockerCompose': docker_compose,
            'rancherCompose': rancher_compose}
        end_point = '{}/projects/{}/stack'.format(
            API.V2_BETA, config.RANCHER_PROJECT_ID)
        response = http_util.post(end_point, payload)
        if response.status_code not in range(200, 300):
            if json.loads(response.text)['code'] == 'NotUnique':
                print 'Oops! Stack already exists. Let`s upgrade it...'
                self.upgrade(name, docker_compose_path, rancher_compose_path)
            else:
                shutdown.err(response.text)
        stack_id = self.get_stack_id(name)
        self.__wait_for_active(stack_id)
        self.__wait_for_healthy(stack_id)
        print 'Stack ' + name + ' created'

    def __init_upgrade(self, name, docker_compose_path, rancher_compose_path):
        print 'Initializing stack ' + name + ' upgrade...'
        docker_compose = self.__get_docker_compose(docker_compose_path)
        rancher_compose = self.__get_rancher_compose(rancher_compose_path)

        payload = {'type': 'environment',
                   'startOnCreate': True,
                   'name': name,
                   'dockerCompose': docker_compose,
                   'rancherCompose': rancher_compose}
        end_point = '{}/environments/{}/?action=upgrade'.format(
            API.V1, self.get_stack_id(name))
        response = http_util.post(end_point, payload)
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)
        print 'Stack upgrade initialized'

    def __finish_upgrade(self, stack_id):
        end_point = '{}/environments/{}/?action=finishupgrade'.format(
            API.V1, stack_id)
        response = http_util.post(end_point, {})
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)

    def __wait_for_upgrade(self, stack_id):
        print 'Let\'s wait until stack upgraded...'

        timeout = config.STACK_UPGRADE_TIMEOUT
        stop_time = int(time()) + timeout
        state = None
        while int(time()) <= stop_time:
            state = self.__get_state(stack_id)
            if state == 'upgraded':
                print 'Stack ' + stack_id + ' upgraded'
                return
            sleep(5)
        shutdown.err(
            'Timeout while waiting to service upgrade. Current state is: ' + state)

    def __wait_for_active(self, stack_id):
        print 'Let`s wait until stack become active...'
        timeout = config.STACK_ACTIVE_TIMEOUT
        stop_time = int(time()) + timeout
        state = None
        while int(time()) <= stop_time:
            state = self.__get_state(stack_id)
            if state == 'active':
                print 'Stack ' + stack_id + ' active'
                return
            sleep(5)
        shutdown.err(
            'Timeout while waiting to service upgrade. Current state is: ' + state)

    def __wait_for_healthy(self, stack_id):
        print 'Let`s wait until stack become healthy...'
        timeout = config.STACK_HEALTHY_TIMEOUT
        stop_time = int(time()) + timeout
        health_state = None
        while int(time()) <= stop_time:
            health_state = self.__get_health_state(stack_id)
            if health_state == 'healthy':
                print 'Stack ' + stack_id + ' is now healthy'
                return
            sleep(5)
        shutdown.err(
            'Timeout while waiting to stack become healthy. Current health state is: ' +
            health_state)

    def __get(self, stack_id):
        end_point = '{}/environments/{}'.format(API.V1, stack_id)
        response = http_util.get(end_point)
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)
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
        except IOError, ex:
            shutdown.err(
                'Could not open docker-compose file: {}\n{}'.format(
                    docker_compose_path, ex.message))

    @staticmethod
    def __get_rancher_compose(rancher_compose_path):
        if rancher_compose_path is None:
            return ''
        else:
            try:
                with open(rancher_compose_path) as file_object:
                    return file_object.read()
            except IOError, ex:
                shutdown.err(
                    'Could not open rancher-compose file: {}\n{}'.format(
                        rancher_compose_path, ex.message))

    def upgrade(self, name, docker_compose_path, rancher_compose_path):
        """Upgrade stack"""

        stack_id = self.get_stack_id(name)
        self.__init_upgrade(name, docker_compose_path, rancher_compose_path)
        self.__wait_for_upgrade(stack_id)
        self.__finish_upgrade(stack_id)
        self.__wait_for_healthy(stack_id)
