"""Defines packaging and distribution."""
from setuptools import setup, find_packages
from disease import __version__

setup(version=__version__, packages=find_packages())
