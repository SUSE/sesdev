# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='sesdev',
    version='1.0.0',
    py_modules=['sesdev'],
    packages=['seslib'],
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