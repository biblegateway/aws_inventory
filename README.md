# aws_inventory  

A dynamic AWS inventory for Ansible - https://pypi.org/project/aws_inventory/  

Install examples:  
  * pip install aws_inventory  
  * pip install git+https://github.com/zahna/aws_inventory.git#egg=master  
  * pip install -e git+https://github.com/zahna/aws_inventory.git#egg=master  

git clone https://github.com/zahna/aws_inventory.git#egg=master  
pip install -e /path/to/aws_inventory  

## Config file options  

First, see the examples/ directory for example files that use aws_inventory.  

Hostnames in the config file can use tags or metadata.  

Metadata examples:  
  * EC2 tags such as "Name"  
  * InstanceId  
  * PublicDnsName  
  * PublicIpAddress  
  * PrivateIpAddress  
  * PrivateDnsName  

## Using an AWS profile credentials

aws_inventory can use an AWS profile's credentials. If the environment variable AWS_PROFILE is set, aws_inventory will use it.


