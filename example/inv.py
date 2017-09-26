#!/usr/bin/env python
# Dynamic inventory script that is designed for our EC2 environment

import sys
sys.dont_write_bytecode = True
from aws_inventory import *

if __name__ == "__main__":
  inv = aws_inventory("./inv.yaml")
  inv.run()
  inv.output()

