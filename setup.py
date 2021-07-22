#!/usr/bin/env python
"""Onedata filesystem Jupyter Contents Manager."""

from setuptools import setup

__version__ = '21.02.0-alpha18'

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Topic :: System :: Filesystems",
]

with open("README.md", "rt") as f:
    DESCRIPTION = f.read()

REQUIREMENTS = ["fs", "six"]

setup(
    name="onedatafs_jupyter",
    author="Bartek Kryza",
    author_email="bkryza@gmail.com",
    classifiers=CLASSIFIERS,
    description="Onedata filesystem Jupyter Contents Manager",
    install_requires=REQUIREMENTS,
    license="MIT",
    long_description=DESCRIPTION,
    packages=["onedatafs_jupyter"],
    keywords=["Jupyter", "Onedata", "oneclient"],
    platforms=["linux"],
    test_suite="nose.collector",
    url="https://github.com/onedata/onedatafs-jupyter",
    version=__version__
)
