#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import codecs

from setuptools import setup

with open("requirements.txt") as f:
    install_requires = [
        line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")
    ]

# Read the constant without importing runtime dependencies or rewriting README.
with open("kipp/__init__.py") as f:
    version = re.search(r'__version__ = "([^"]+)"', f.read()).group(1)


with codecs.open("README.md", "r", "utf8") as f:
    long_description = f.read()


name = "kipp"
packages = []
package_dir = {name: name}
for dirname, dirnames, filenames in os.walk(name):
    if "__init__.py" in filenames:
        packages.append(dirname.replace("/", "."))

extras = {
    "test": ["pytest>=8,<10", "mock>=5.2,<6"],
    "doc": ["sphinx>=8.1,<10", "myst-parser>=4,<6"],
    "image": ["pillow>=12.3,<13"],
    "aio": ["tornado>=6.5.10,<7"],
}
all_extras = []
for _, v in extras.items():
    all_extras.extend(v)

extras["all"] = all_extras

data_files = [
    "requirements.txt",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "Makefile",
    "package.json",
    "tox.ini",
]

setup(
    name=name,
    version=version,
    python_requires=">=3.10",
    packages=packages,
    package_dir=package_dir,
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras,
    data_files=data_files,
    author="Laisky",
    author_email="ppcelery@gmail.com",
    description="Python Utils",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Laisky/kipp",
    license="MIT License",
    entry_points="""\
        [console_scripts]
        kipp_runner=kipp.runner.__main__:main
    """,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
    keywords=["setup", "distutils", "utils"],
)
