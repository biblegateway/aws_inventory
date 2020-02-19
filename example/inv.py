#!/usr/bin/env python
# Dynamic inventory script that is designed for our EC2 environment

import os
from aws_inventory import *

# Get this script's working directory
wd = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
  inv = aws_inventory("{}/inv.yml".format(wd))
  print(inv.run())

