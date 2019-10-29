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
        "astroid >= 1.6.1",
        "Click >= 6.7",
        "isort >= 4.2.15",
        "Jinja2 >= 2.10.1",
        "lazy-object-proxy >= 1.2.2",
        "MarkupSafe >= 1.0",
        "mccabe >= 0.6.1",
        "pycryptodome >= 3.4.7",
        "PyYAML >= 3.13",
        "six >= 1.11.0",
        "typed-ast >= 1.3.1",
        "wrapt >= 1.10.10"
    ],
    entry_points={
        'console_scripts': [
            'sesdev = sesdev:cli'
        ]
    }
)