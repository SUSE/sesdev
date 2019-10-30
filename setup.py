# -*- coding: utf-8 -*-
from setuptools import setup

import os
import re


def get_version_from_spec():
    this_dir = os.path.dirname(__file__)
    with open(os.path.join(this_dir, 'sesdev.spec'), 'r') as file:
        while True:
            line = file.readline()
            if not line:
                return 'unknown'
            m = re.match(r'^Version:\s+(\d.*)', line)
            if m:
                return m[1]

setup(
    name='sesdev',
    version=get_version_from_spec(),
    py_modules=['sesdev'],
    packages=['seslib'],
    package_data={
        'seslib': ['templates/*.j2']
    },
    install_requires=[
        "Click >= 6.7",
        "Jinja2 >= 2.10.1",
        "pycryptodomex >= 3.4.6",
        "PyYAML >= 3.13"
    ],
    entry_points={
        'console_scripts': [
            'sesdev = sesdev:cli'
        ]
    }
)