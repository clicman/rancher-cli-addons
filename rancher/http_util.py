"""Simple HTTP util for Rancher API"""

import requests
from . import config

_GET = 'get'
_POST = 'post'
_PUT = 'put'

_HTTP = {
    _GET: requests.get,
    _POST: requests.post,
    _PUT: requests.put
}

_HEADERS = {'Content-Type': 'application/json', 'Accept': 'application/json'}


def _send_request(method, url, json_data=None):
    """Send HTTP request"""
    return _HTTP[method]('{}/{}/'.format(config.RANCHER_BASE_URL, url),
                         auth=(config.RANCHER_API_ACCESS_KEY, config.RANCHER_API_SECRET_KEY),
                         headers=_HEADERS, json=json_data, verify=False)


def get(url):
    """Sends get request"""
    return _send_request(_GET, url)


def post(url, payload):
    """Sends post request"""
    return _send_request(_POST, url, payload)


def put(url, payload):
    """Sends put request"""
    return _send_request(_PUT, url, payload)
