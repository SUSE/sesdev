# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='sesdev',
    version='1.0.0',
    py_modules=['sesdev'],
    packages=['seslib'],
    install_requires=[
        "astroid==2.3.2",
        "Click==7.0",
        "isort==4.3.21",
        "Jinja2==2.10.3",
        "lazy-object-proxy==1.4.2",
        "MarkupSafe==1.1.1",
        "mccabe==0.6.1",
        "pycryptodome==3.9.0",
        "pylint==2.4.3",
        "PyYAML==5.1.2",
        "six==1.12.0",
        "typed-ast==1.4.0",
        "wrapt==1.11.2"
    ],
    entry_points={
        'console_scripts': [
            'sesdev = sesdev:cli'
        ]
    }
)