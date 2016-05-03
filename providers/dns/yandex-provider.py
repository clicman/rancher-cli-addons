import json
import requests

from providers.dns import DnsProvider


class YandexProvider(DnsProvider):
    __base_url = 'https://pddimp.yandex.ru/api2/admin'
    __request_headers = {}

    def add_record(self, fqdn, ip, ttl=360):

        domain = '.'.join(fqdn.split('.')[-2:])
        subdomain = '.'.join(fqdn.split('.')[:-2])

        params = {'domain': domain, 'type': 'A', 'subdomain': subdomain, 'ttl': ttl, 'content': ip}
        end_point = self.__base_url + '/dns/add'
        response = requests.post(end_point,
                                 headers=self.__request_headers, params=params)

        if response.status_code not in range(200, 300) or (
                        json.loads(response.text)['success'] == 'error' and json.loads(response.text)[
                    'error'] != 'record_exists'):
            print 'Failed to add domain: ' + response.text
            exit(2)

    def remove_record(self, domain_name, fqdn):
        record_id = self.__get_record_id(domain_name, fqdn)
        if record_id is None:
            print 'No such domain'
            exit(0)
        params = {'domain': domain_name, 'record_id': record_id}
        end_point = self.__base_url + '/dns/del'
        response = requests.post(end_point,
                                 headers=self.__request_headers, params=params)

        if response.status_code not in range(200, 300) or (
                        json.loads(response.text)['success'] == 'error' and json.loads(response.text)[
                    'error'] != 'no_such_record'):
            print 'Failed to remove domain: ' + response.text
            exit(2)

    def __get_record_id(self, domain_name, fqdn):
        end_point = self.__base_url + '/dns/list?domain=' + domain_name
        response = requests.get(end_point, headers=self.__request_headers)

        if response.status_code not in range(200, 300) or json.loads(response.text)['success'] == 'error':
            print response.text
            exit(2)

        records = json.loads(response.text)['records']
        for record in records:
            if record['fqdn'] == fqdn:
                return record['record_id']
        return None
