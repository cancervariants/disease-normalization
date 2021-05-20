"""Defines packaging and distribution."""
from setuptools import setup

exec(open('disease/version.py').read())
setup(version=__version__)  # noqa: F821
