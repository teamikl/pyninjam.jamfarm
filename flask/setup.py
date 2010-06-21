from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='JamFarmPortal',
      version=version,
      description="Prototype of JamFarm portal site",
      long_description="""\
JamFarm portal (flask based)""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='ninjam',
      author='tea',
      author_email='teamikl@hotmail.com',
      url='http://localhost:8000/',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
