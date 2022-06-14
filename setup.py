#!/usr/bin/env python

import os
#from distutils.core import setup
from setuptools import setup

def read(fname):
  return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
  name='aws_inventory',
  version='0.5.8',
  author='Scott Zahn',
  author_email='scott@zahna.com',
  packages=['aws_inventory'],
  description='A dynamic AWS inventory for Ansible which groups nodes using regular expressions.',
  long_description=read('README.md'),
  long_description_content_type="text/markdown",
  url='https://github.com/zahna/aws_inventory',
  download_url='https://pypi.python.org/pypi/aws_inventory',
  license='License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
  platforms='any',
  install_requires=['boto3>=1.7.0', 'pyyaml>=5.1'],
  classifiers=[
    'Development Status :: 4 - Beta',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Topic :: System :: Systems Administration'
  ]
)

