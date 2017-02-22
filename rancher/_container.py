""" Manages containers """

import json
from rancher import shutdown
from rancher import API, http_util


class Container(object):
    """ Manages containers """

    def __get(self, instance_id):
        end_point = '{}/containers/{}'.format(API.V2_BETA, instance_id)

        response = http_util.get(end_point)
        if response.status_code not in range(200, 300):
            shutdown.err(response.text)
        return json.loads(response.text)

    def get_host_id(self, instance_id):
        """Get host id by instance id"""
        return self.__get(instance_id)['hostId']

    def get_container_id(self, instance_id):
        """Get container id by instance id"""
        return self.__get(instance_id)['externalId']
