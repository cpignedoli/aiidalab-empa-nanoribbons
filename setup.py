"""Setting up nanoribbons app for AiiDA"""
from __future__ import absolute_import

import json

from io import open  # pylint: disable=redefined-builtin
from setuptools import setup, find_packages


def run_setup():
    with open('setup.json', 'r', encoding='utf-8') as info:
        kwargs = json.load(info)
    setup(include_package_data=True,
          packages=find_packages(),
          long_description=open('README.md', encoding='utf-8').read(),
          long_description_content_type='text/markdown',
          **kwargs)


if __name__ == '__main__':
    run_setup()