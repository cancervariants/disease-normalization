"""Defines packaging and distribution."""
from setuptools import setup

setup(name='disease-normalization',
      version='0.0.1',
      description='VICC normalization routine for diseases',
      url='https://github.com/cancervariants/disease-normalization',
      author='VICC',
      author_email='help@cancervariants.org',
      license='MIT',
      packages=['disease'],
      zip_safe=False)
