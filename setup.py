#!/usr/bin/env python
from distutils.core import setup

setup(name='photo-sorter.py',
      description='Image sorting utility',
      version='0.2',
      scripts=['photo-sorter.py'],
      requires=['pyexiv2==0.3.0'],
      author='Marcin Biernat',
      author_email='mb@marcinbiernat.pl',
      url='http://github.com/biern/photo-sorter.py'
      )
