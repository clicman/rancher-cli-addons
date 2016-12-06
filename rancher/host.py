import json

import re

from rancher import exit, util
import requests


class Host:
    rancherApiVersion = '/v1/'
    request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def __init__(self, configuration):
        self.config = configuration

    def get_available_port(self, host_id, start, end):
        ports = self.__get_host_ports(host_id)
        available_range = range(start, end+1)
        for port in ports:
            if port in available_range:
                available_range.remove(port)

        if len(available_range) > 0:
            return available_range[0]
        exit.err('There is no available ports')

    def __get_host_ports(self, host_id):
        end_point = self.config['rancherBaseUrl'] + self.rancherApiVersion + 'hosts/' + host_id
        response = requests.get(end_point,
                                auth=(self.config['rancherApiAccessKey'], self.config['rancherApiSecretKey']),
                                headers=self.request_headers, verify=False)
        if response.status_code not in range(200, 300):
            exit.err(response.text)

        data = json.loads(response.text)
        public_endpoints = data['publicEndpoints']
        ports = []
        for endpoint in public_endpoints:
            ports.append(endpoint['port'])
        return ports
