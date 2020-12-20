# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in pav/__init__.py
from pav import __version__ as version

setup(
	name='pav',
	version=version,
	description='Partner Added Value',
	author='Ahmed Mohammed Alkuhlani',
	author_email='a.kuhlani@partner-cons.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
