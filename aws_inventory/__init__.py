from __future__ import print_function
import os
import sys
import yaml
import json
from botocore.client import Config
import boto3
import re
import random

class aws_inventory(object):
  def __init__(self, config):
    # Read in the config to construct and build host groups. Autodetect if it's a file or string.
    if os.path.isfile(config):
      self.config = yaml.load(open(config, 'r'), Loader=yaml.FullLoader)
    elif type(config) == str:
      self.config = yaml.load(config, Loader=yaml.FullLoader)
      if type(self.config) != dict:
        raise TypeError(f"Inventory config was not able to be parsed properly. Provided inventory config: \"{config}\"")
    else:
      raise TypeError

    # Set some config defaults, if not present
    if not 'hostnames' in self.config: self.config['hostnames'] = {}
    if not 'source' in self.config['hostnames']: self.config['hostnames']['source'] = 'ec2_tag'
    if self.config['hostnames']['source'] == 'ec2_tag' and not 'ec2_tag' in self.config['hostnames']:
      self.config['hostnames']['var'] = 'Name'
    if self.config['hostnames']['source'] == 'ec2_metadata' and not 'ec2_metadata' in self.config['hostnames']:
      self.config['hostnames']['var'] = 'PublicDnsName'
    if not 'ansible_host_var' in self.config: self.config['ansible_host_var'] = 'PublicIpAddress'

    # Set some boto3 config defaults
    if not 'region_name' in self.config['boto3']: self.config['boto3']['region_name'] = 'us-east-1'
    if not 'connect_timeout' in self.config['boto3']: self.config['boto3']['connect_timeout'] = 5
    if not 'read_timeout' in self.config['boto3']: self.config['boto3']['read_timeout'] = 20
    if not 'max_attempts' in self.config['boto3']: self.config['boto3']['max_attempts'] = 10

    # Initialize the needed AWS clients
    aws_config = Config(region_name = self.config['boto3']['region_name'],
                        connect_timeout = self.config['boto3']['connect_timeout'],
                        read_timeout = self.config['boto3']['read_timeout'],
                        retries = {'max_attempts': self.config['boto3']['max_attempts']})
    if 'AWS_PROFILE' in os.environ:
      self.ec2 = boto3.client('ec2', config=aws_config)
      self.rds = boto3.client('rds', config=aws_config)
    elif 'aws_access_key_id' in self.config['boto3'] and 'aws_secret_access_key' in self.config['boto3']:
      self.ec2 = boto3.client('ec2', config=aws_config,
                              aws_access_key_id = self.config['boto3']['aws_access_key_id'],
                              aws_secret_access_key = self.config['boto3']['aws_secret_access_key'])
      self.rds = boto3.client('rds', config=aws_config,
                              aws_access_key_id = self.config['boto3']['aws_access_key_id'],
                              aws_secret_access_key = self.config['boto3']['aws_secret_access_key'])

    # Initialize the inventory
    self.inventory = {}
    self.inventory['_meta'] = {'hostvars': {}}
    self.inventory['all'] = {'hosts': [], 'vars': {}}

    # Add localhost to inventory
    self.inventory['all']['hosts'].append('localhost')
    self.inventory['_meta']['hostvars']['localhost'] = {}
    self.inventory['_meta']['hostvars']['localhost']['ansible_host'] = 'localhost'
    self.inventory['_meta']['hostvars']['localhost']['ec2_public_dns_name'] = 'localhost'
    self.inventory['_meta']['hostvars']['localhost']['ec2_public_ip_address'] = '127.0.0.1'
    self.inventory['_meta']['hostvars']['localhost']['ec2_private_ip_address'] = '127.0.0.1'
    # Add any hostvars for localhost to the inventory
    self.inventory['_meta']['hostvars']['localhost'].update(self._get_hostvars('localhost'))

    # Create empty host groups from the config
    for g in self.config['groups']:
      self.inventory[g['name']] = []

  # Return a dict of hostvars applicable to the host
  def _get_hostvars(self, host):
    hostvars = {}
    if 'hostvars' in self.config and type(self.config['hostvars']) == dict:
      for h in self.config['hostvars']:
        if h[0] == "~":
          if re.search(h[1:], host):
            hostvars.update(self.config['hostvars'][h])
        elif h[0] == "=":
          if h[1:] == host:
            hostvars.update(self.config['hostvars'][h])
        else:
          if h in host:
            hostvars.update(self.config['hostvars'][h])
    return hostvars

  # For sorting
  def alphanum_key(self, s):
    '''http://nedbatchelder.com/blog/200712/human_sorting.html'''
    tryint = lambda s: int(s) if s.isdigit() else s
    return [ tryint(c) for c in re.split('(\d+)', s) ]

  # Formats: json, raw (a raw Python dict)
  def run(self, format='json'):
    # Get EC2 instance data
    aws_resp = self.ec2.describe_instances()
    if aws_resp['ResponseMetadata']['HTTPStatusCode'] != 200:
      print("ERROR: Received HTTP status code {} from AWS. Exiting.".format(aws_resp['ResponseMetadata']['HTTPStatusCode']), file=sys.stderr)
      exit(1)
    # Loop through the AWS response and add the relevant instance info to the inventory
    for item in aws_resp.items():
      #print("{}\n\n".format(dir(item)))
      for i in item[1]:
        # For some reason every ec2 instance is listed inside a dict, under the key "Instances"
        if type(i) == dict:
          for m in i['Instances']:
            hostname = ''
            hostvars = []
            tags = {}
            #print("{}".format(m))
            # If an instance is not running, skip it
            if m['State']['Name'] != 'running': continue
            # If we use an ec2 tag to assign the inventory hostname, find it and use it
            if self.config['hostnames']['source'] == 'ec2_tag':
              if 'Tags' in m:
                found = False
                for t in m['Tags']:
                  if t['Key'] == self.config['hostnames']['var']:
                    hostname = t['Value']
                    found = True
                    break
                if not found:
                  print("WARNING: Instance {} has no tag \"{}\". Skipping.".format(m['InstanceId'], self.config['hostnames']['var']), file=sys.stderr)
                  continue
              # If instance has no ec2 tags, skip it.
              else:
                print("WARNING: Instance {} has no tags. Skipping.".format(m['InstanceId']), file=sys.stderr)
                continue
            # If we use an ec2 metadata variable to assign the inventory hostname, find it and use it
            if self.config['hostnames']['source'] == 'ec2_metadata':
              if self.config['hostnames']['var'] in m:
                hostname = m[self.config['hostnames']['var']]
              else:
                print("WARNING: Instance {} has no metadata variable \"{}\". Skipping.".format(m['InstanceId'], self.config['hostnames']['var']), file=sys.stderr)
                continue
            # Prep host's ec2 tags for inclusion in inventory
            for t in m['Tags']:
              tags['ec2_tag_%s' % t['Key'].replace(':', '_')] = t['Value']
            # Add host to group 'all'
            self.inventory['all']['hosts'].append(hostname)
            # Add any hostvars for the host to the inventory
            self.inventory['_meta']['hostvars'][hostname] = {}
            self.inventory['_meta']['hostvars'][hostname].update(tags)
            self.inventory['_meta']['hostvars'][hostname].update(self._get_hostvars(hostname))

            # The hostvar "ansible_host" is what ansible uses when ssh'ing to the host.
            if self.config['ansible_host_var'] in m.keys():
              self.inventory['_meta']['hostvars'][hostname]['ansible_host'] = m[self.config['ansible_host_var']]
            else:
              print("ERROR: can not set hostvar \"ansible_host\" on \"{}\". ec2 metadata \"{}\" missing. Exiting.".format(hostname, self.config['ansible_host_var']), file=sys.stderr)
              exit(1)

            self.inventory['_meta']['hostvars'][hostname]['ec2_private_ip_address'] = m['PrivateIpAddress']
            if 'PublicDnsName' in m.keys():
              self.inventory['_meta']['hostvars'][hostname]['ec2_public_dns_name'] = m['PublicDnsName']
            else:
              print("WARNING: no PublicDnsName for host -- {}.".format(m), file=sys.stderr)
            if 'PublicIpAddress' in m.keys():
              self.inventory['_meta']['hostvars'][hostname]['ec2_public_ip_address'] = m['PublicIpAddress']
            else:
              print("WARNING: no PublicIpAddress for host -- {}".format(m), file=sys.stderr)



    # TODO: Get relevant RDS instance data and add it to the inventory
    #for item in self.rds.describe_db_instances().items():
    #  #print("{}\n\n".format(dir(item)))
    #  for i in item[1]:
    #    print(item)


    # TODO: Get relevant ElastiCache instance data and add it to the inventory


    # Lastly with hosts, add local nodename to inventory, if not already present
    local_nodename = os.uname()[1]
    if local_nodename not in self.inventory['all']['hosts']:
      self.inventory['all']['hosts'].append(local_nodename)
      self.inventory['_meta']['hostvars'][local_nodename] = {}
      self.inventory['_meta']['hostvars'][local_nodename]['ansible_host'] = local_nodename
      self.inventory['_meta']['hostvars'][local_nodename]['ec2_public_dns_name'] = local_nodename
      self.inventory['_meta']['hostvars'][local_nodename]['ec2_public_ip_address'] = '127.0.0.1'
      self.inventory['_meta']['hostvars'][local_nodename]['ec2_private_ip_address'] = '127.0.0.1'
      # Add any hostvars for localhost to the inventory
      self.inventory['_meta']['hostvars'][local_nodename].update(self._get_hostvars(local_nodename))

    # Iterate through each host group, adding hosts from group "all" that match
    for g in self.config['groups']:
      self.inventory[g['name']] = {'hosts': [], 'vars': {}}
      if 'vars' in g: self.inventory[g['name']]['vars'].update(g['vars'])
      for h in self.inventory['all']['hosts']:
        # Test whether the metadata hostvar we group by is in the host's metadata and that its value matches
        if g['hostvar'] in self.inventory['_meta']['hostvars'][h] and re.search(g['match'], self.inventory['_meta']['hostvars'][h][g['hostvar']]):
          self.inventory[g['name']]['hosts'].append(h)

    # Per group, shuffle host order if specified
    for group in self.config['groups']:
      if 'order' in group:
        if group['order'].lower() == 'shuffle':
          random.shuffle(self.inventory[group['name']]['hosts'])
        elif group['order'].lower() == 'sorted':
          self.inventory[group['name']]['hosts'].sort(key=self.alphanum_key)

    # Return the inventory for outputting
    if format == 'json':
      return json.dumps(self.inventory, sort_keys=True, indent=2, separators=(',', ': '))
    elif format == 'raw':
      return self.inventory


