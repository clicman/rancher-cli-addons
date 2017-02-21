import json
import requests
from rancher import exit
from rancher import API


class Container:
    rancherApiVersion = '/v1/'
    request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def __init__(self, configuration):
        self.config = configuration

    def __get(self, instance_id):
        end_point = self.config['rancherBaseUrl'] + "/" + API.V2_BETA + '/containers/' + instance_id
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)
        return json.loads(response.text)

    def get_host_id(self, instance_id):
        return self.__get(instance_id)['hostId']

    def get_container_id(self, instance_id):
        return self.__get(instance_id)['externalId']
