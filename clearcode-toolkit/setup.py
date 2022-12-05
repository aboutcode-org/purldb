#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import io
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext
import re

from setuptools import find_packages
from setuptools import setup


setup(
    name='clearcode-toolkit',
    version='0.0.3',
    license='Apache-2.0',
    description='ClearCode is a tool to sync ClearlyDefined data.',
    long_description='ClearCode is a tool to sync ClearlyDefined scans and curations.',
    author='nexB Inc. and others',
    author_email='info@aboutcode.org',
    url='https://github.com/nexB/clearcode-toolkit',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities',
    ],
    keywords=[
        'open source',
        'scan',
        'license',
        'package',
        'clearlydefined',
        'scancode', 
    ],
    install_requires=[
        'attrs',
        'click',
        'django',
        'psycopg2',
        'requests',
        'djangorestframework',
        'packageurl-python',
    ],
    entry_points={
        'console_scripts': [
            'clearsync = clearcode.sync:cli',
            'clearload = clearcode.load:cli',
        ],
    },
)
