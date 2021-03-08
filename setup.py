"""Defines packaging and distribution."""
from setuptools import setup, find_packages
from disease import __version__  # noqa

setup(packages=find_packages())
