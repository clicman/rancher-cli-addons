import json

import re

from rancher import exit, util, service
import requests


class Host:
    rancherApiVersion = '/v1/'
    request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def __init__(self, configuration):
        self.config = configuration

    def get_available_port(self, stack_svc, host_id, start, end):
        service_id = None
        if stack_svc is not None:
            service_id = service.Service(self.config).parse_service_id(stack_svc)

        ports = self.__get_host_ports(host_id)
        available_range = range(start, end+1)
        for port in ports:
            if port['port'] in available_range:
                if port['serviceId'] == service_id:
                    return port['port']
                available_range.remove(port['port'])

        if len(available_range) > 0:
            return available_range[0]
        exit.err('There is no available ports')

    def __get(self, host_id):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'hosts/' + host_id
        response = requests.get(end_point,
                        auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                        headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

        return json.loads(response.text)

    def __get_host_ports(self, host_id):
        data = self.__get(host_id)
        public_endpoints = data['publicEndpoints']
        ports = []
        for endpoint in public_endpoints:
            ports.append(endpoint['port'])
        return public_endpoints

    def get_host_ip(self, host_id):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'hosts/' + host_id
        response = requests.get(end_point,
                            auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                            headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

        data = json.loads(response.text)
        if data['publicEndpoints']:
            return data['publicEndpoints'][0]['ipAddress']
        else:
            exit.err('There is no public endpoints on host ' + host_id)


