"""Defines packaging and distribution."""
from setuptools import setup, find_packages
from disease.__version__ import __version__  # noqa

setup(version=__version__, packages=find_packages())
