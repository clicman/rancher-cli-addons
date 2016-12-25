#!/usr/bin/env python
import json
import os
import requests

import argparse

base_url = 'https://pddimp.yandex.ru/api2/admin'

parser = argparse.ArgumentParser(description='Domain manager for http://pdd.yandex.ru service')
parser.add_argument('action', help='add or remove')
parser.add_argument('domain', help='domain name')
parser.add_argument('--ip', help='Domain ip')
parser.add_argument('--ttl', default=360, help='Ttl dor domain. default is 360 seconds')
parser.add_argument('--token', default=os.environ.get('PDD_TOKEN'),
                    help='api access token, $PDD_TOKEN environment variable can be used')

request_headers = {}


def main():
    args = []
    try:
        args = parser.parse_args()
    except SystemExit:
        parser.parse_args(['-h'])
        exit(1)

    if args.token is None:
        print ('Api token not defined')
        parser.parse_args(['-h'])
        exit(1)

    request_headers['PddToken'] = args.token

    domain = '.'.join(args.domain.split('.')[-2:])
    subdomain = '.'.join(args.domain.split('.')[:-2])

    if args.action == 'add':
        if args.ip is None:
            print ('Ip not set')
            parser.parse_args(['-h'])
            exit(2)
        add(domain, subdomain, args.ttl, args.ip)
    elif args.action == 'remove':
        remove(domain, args.domain)


def add(domain_name, subdomain_name, ttl, ip):
    params = {'domain': domain_name, 'type': 'A', 'subdomain': subdomain_name, 'ttl': ttl, 'content': ip}
    end_point = base_url + '/dns/add'
    response = requests.post(end_point,
                             headers=request_headers, params=params)

    if response.status_code not in range(200, 300) or (
                    json.loads(response.text)['success'] == 'error' and
                    json.loads(response.text)['error'] != 'record_exists'):
        print ('Failed to add domain: ' + response.text)
        exit(2)


def remove(domain_name, fqdn):
    record_id = __get_record_id(domain_name, fqdn)
    if record_id is None:
        print ('No such domain')
        exit(0)
    params = {'domain': domain_name, 'record_id': record_id}
    end_point = base_url + '/dns/del'
    response = requests.post(end_point,
                             headers=request_headers, params=params)

    if response.status_code not in range(200, 300) or (
                    json.loads(response.text)['success'] == 'error' and
                    json.loads(response.text)['error'] != 'no_such_record'):
        print ('Failed to remove domain: ' + response.text)
        exit(2)


def __get_record_id(domain_name, fqdn):
    end_point = base_url + '/dns/list?domain=' + domain_name
    response = requests.get(end_point, headers=request_headers)

    if response.status_code not in range(200, 300) or json.loads(response.text)['success'] == 'error':
        print (response.text)
        exit(2)

    records = json.loads(response.text)['records']
    for record in records:
        if record['fqdn'] == fqdn:
            return record['record_id']
    return None


main()
