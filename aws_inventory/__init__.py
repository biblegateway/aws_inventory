from __future__ import print_function
import yaml
import json
import boto3
import re
import random

class aws_inventory(object):
  def __init__(self, config):
    # Initialize the inventory
    self.inventory = {}
    self.inventory['all'] = {'hosts': [], 'vars': {}}
    self.inventory['_meta'] = {'hostvars': {}}
    # Add localhost to inventory
    self.inventory['all']['hosts'].append('localhost')
    self.inventory['_meta']['hostvars']['localhost'] = {}
    self.inventory['_meta']['hostvars']['localhost']['ansible_host'] = 'localhost'
    self.inventory['_meta']['hostvars']['localhost']['ec2_public_dns_name'] = 'localhost'
    self.inventory['_meta']['hostvars']['localhost']['ec2_public_ip_address'] = '127.0.0.1'
    self.inventory['_meta']['hostvars']['localhost']['ec2_private_ip_address'] = '127.0.0.1'
    self.inventory['_meta']['hostvars']['localhost']['ansible_connection'] = 'local'

    # Read in the config to construct and build host groups
    self.config = yaml.load(open(config, 'r'))
    # Set some config defaults, if not present
    if not 'hostnames' in self.config: self.config['hostnames'] = {}
    if not 'source' in self.config['hostnames']: self.config['hostnames']['source'] = 'ec2_tag'
    if self.config['hostnames']['source'] == 'ec2_tag' and not 'ec2_tag' in self.config['hostnames']:
      self.config['hostnames']['var'] = 'Name'
    if self.config['hostnames']['source'] == 'ec2_metadata' and not 'ec2_metadata' in self.config['hostnames']:
      self.config['hostnames']['var'] = 'PublicDnsName'

    # Create empty host groups from the config
    for g in self.config['groups']:
      self.inventory[g['name']] = []

    # These creds are for our IAM user "ansible_deploy"
    self.ec2 = boto3.client('ec2', region_name = self.config['boto3']['region_name'],
                          aws_access_key_id = self.config['boto3']['aws_access_key_id'],
                          aws_secret_access_key = self.config['boto3']['aws_secret_access_key'])
    #print(dir(ec2))
    self.rds = boto3.client('rds', region_name = self.config['boto3']['region_name'],
                          aws_access_key_id = self.config['boto3']['aws_access_key_id'],
                          aws_secret_access_key = self.config['boto3']['aws_secret_access_key'])

  def alphanum_key(self, s):
    '''http://nedbatchelder.com/blog/200712/human_sorting.html'''
    tryint = lambda s: int(s) if s.isdigit() else s
    return [ tryint(c) for c in re.split('(\d+)', s) ]

  def run(self):
    # Get relevant EC2 instance data and add it to the inventory
    for item in self.ec2.describe_instances().items():
      #print("%s\n\n" % dir(item))
      for i in item[1]:
        # For some reason every ec2 instance is listed inside a dict, under the key "Instances"
        if type(i) == dict:
          for m in i['Instances']:
            # If it's not running, skip it
            if m['State']['Name'] != 'running': continue
            # If instance has no ec2 tags, skip it.
            if 'Tags' not in m:
              print("WARNING: Instance %s has no tags -- %s" % (m['InstanceId'], m), file=sys.stderr)
              continue
            #print("%s" % m)
            hostname = ''
            hostvars = []
            tags = {}
            # If the meta var matches what we use to assign hostnames with, use the value as the hostname
            if self.config['hostnames']['source'] == 'ec2_metadata' and self.config['hostnames']['var'] in m:
              hostname = m[self.config['hostnames']['var']]
            # Go through ec2 tags
            for t in m['Tags']:
              tags['ec2_tag_%s' % t['Key'].replace(':', '_')] = t['Value']
              # If the tag matches what we use to assign hostnames with, use the value as the hostname
              if self.config['hostnames']['source'] == 'ec2_tag' and t['Key'] == self.config['hostnames']['var']:
                hostname = t['Value']
            # Add to 'all'
            self.inventory['all']['hosts'].append(hostname)
            # Add hostvars for the host to the inventory
            self.inventory['_meta']['hostvars'][hostname] = {}
            self.inventory['_meta']['hostvars'][hostname].update(tags)
            if 'PublicDnsName' in m.keys():
              self.inventory['_meta']['hostvars'][hostname]['ansible_host'] = m['PublicDnsName']
              self.inventory['_meta']['hostvars'][hostname]['ec2_public_dns_name'] = m['PublicDnsName']
            else:
              print("ERROR: no PublicDnsName for host -- %s" % m, file=sys.stderr)
              print("Aborting.", file=sys.stderr)
              exit(1)
            if 'PublicIpAddress' in m.keys():
              self.inventory['_meta']['hostvars'][hostname]['ec2_public_ip_address'] = m['PublicIpAddress']
            else:
              print("WARNING: no PublicIpAddress for host -- %s" % m, file=sys.stderr)
            self.inventory['_meta']['hostvars'][hostname]['ec2_private_ip_address'] = m['PrivateIpAddress']

    # TODO: Get relevant RDS instance data and add it to the inventory
    #for item in self.rds.describe_db_instances().items():
    #  #print("%s\n\n" % dir(item))
    #  for i in item[1]:
    #    print(item)


    # TODO: Get relevant ElastiCache instance data and add it to the inventory


    # Iterate through "all", and add hosts to groups
    for h in self.inventory['all']['hosts']:
    #  if ' ' in h: continue
      for g in self.config['groups']:
        if g['hostvar'] in self.inventory['_meta']['hostvars'][h] and re.search(g['match'], self.inventory['_meta']['hostvars'][h][g['hostvar']]):
    #      inventory[g['name']].append(inventory['_meta']['hostvars'][h]['ec2_public_ip_address'])
          self.inventory[g['name']].append(h)

    # Per group, shuffle host order if specified
    for group in self.config['groups']:
      if 'order' in group:
        if group['order'].lower() == 'shuffle':
          random.shuffle(self.inventory[group['name']])
        elif group['order'].lower() == 'sorted':
          self.inventory[group['name']].sort(key=self.alphanum_key)

  def output(self, format='json'):
    if format == 'json':
      # Output the inventory
      print(json.dumps(self.inventory, sort_keys=True, indent=2, separators=(',', ': ')))


