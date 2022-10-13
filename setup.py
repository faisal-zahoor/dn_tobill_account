# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in dn_tobill_account/__init__.py
from dn_tobill_account import __version__ as version

setup(
	name='dn_tobill_account',
	version=version,
	description='Delivery Note To Bill Account',
	author='SMB Solutions',
	author_email='jaypatel16@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
