#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import codecs

try:
    import setuptools
    from setuptools import setup
except ImportError:
    setuptools = None
    from distutils.core import setup
from pip.req import parse_requirements
from pip.download import PipSession

import kipp


requires = [str(i.req) for i in parse_requirements('requirements.txt',
                                                   session=PipSession())
            if i.req is not None]


def update_readme_version(version):
    ver_reg = re.compile(
        '(https://img\.shields\.io/badge/version-v'
        '[0-9]+\.[0-9]+(\.[0-9]+)?((dev|rc)[0-9]+)?'
        '-blue\.svg)'
    )
    _v = 'https://img.shields.io/badge/version-v{}-blue.svg'.format(version)
    with open('README.md', 'r') as f:
        src = f.read()

    with open('README.md', 'w') as f:
        dest = ver_reg.sub(_v, src)
        f.write(dest)


version = kipp.__version__
update_readme_version(version)

with codecs.open('README.md', 'r', 'utf8') as f:
    long_description = f.read()


name = 'kipp'
packages = []
package_dir = {name: name}
for dirname, dirnames, filenames in os.walk(name):
    if '__init__.py' in filenames:
        packages.append(dirname.replace('/', '.'))

extras = {
    'test': ['pytest', 'mock'],
    'doc': ['sphinx', 'recommonmark', 'sphinxcontrib-napoleon'],
    'image': ['pillow==3.4.2',],
}
all_extras = []
for _, v in extras.items():
    all_extras.extend(v)

extras['all'] = all_extras

data_files = [
    'requirements.txt',
    'README.md',
    'CHANGELOG.md',
    'LICENSE',
    'Makefile',
    'package.json',
    'tox.ini',
]

setup(
    name=name,
    version=version,
    packages=packages,
    package_dir=package_dir,
    include_package_data=True,
    install_requires=requires,
    extras_require=extras,
    data_files=data_files,
    author='Laisky',
    author_email='ppcelery@gmail.com',
    description='Python Utils',
    long_description=long_description,
    url='https://github.com/Laisky/kipp',
    license='MIT License',
    entry_points="""\
        [console_scripts]
        kipp_runner=kipp.runner.__main__:main
    """,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Development Status :: 4 - Beta',
        'Topic :: Software Development :: Libraries',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
    ],
    keywords=[
        'setup',
        'distutils',
        'utils',
    ]
)
