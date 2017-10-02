import os
#from distutils.core import setup
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
  name='aws_inventory',
  version='0.1.0',
  author='Scott Zahn',
  author_email='scott@zahna.com',
  packages=['aws_inventory'],
  description='A simple dynamic AWS inventory for Ansible',
  long_description=read('README.md'),
  url='https://github.com/zahna/aws_inventory',
  download_url='https://pypi.python.org/pypi/aws_inventory',
  license='License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
  platforms='any',
  install_requires=['boto3', 'pyyaml'],
  classifiers=[
    'Development Status :: 4 - Beta',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Topic :: System :: Systems Administration'
  ]
)

