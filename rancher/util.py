import json


def build_payload(source):
    payload = json.dumps(source)
    return payload
