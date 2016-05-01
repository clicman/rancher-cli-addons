import yaml
import argparse

parser = argparse.ArgumentParser(description='Yaml values modifier')
parser.add_argument('file', help='Path to file')
parser.add_argument('prop', help='FQDN property path')
parser.add_argument('value', help='property value')

try:
    parser.parse_args()
except:
    parser.parse_args(['-h'])


def parse(yml_file):
    with open(yml_file, 'r') as stream:
        try:
            return yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(2)


args = parser.parse_args()

parsed_yml = parse(args.file)
prop_path = args.prop.split('.')


def get_from_dict(data_dict, map_list):
    return reduce(lambda d, k: d[k], map_list, data_dict)


def set_in_dict(data_ict, map_ist, value):
    get_from_dict(data_ict, map_ist[:-1])[map_ist[-1]] = value


set_in_dict(parsed_yml, prop_path, args.value)
stream = file(args.file, 'w')
yaml.dump(parsed_yml, stream)
