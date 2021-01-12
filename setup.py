# -*- coding: utf-8 -*-

import os
from os import path
from setuptools import setup

here = path.abspath(path.dirname(__file__))
readme_file = os.path.join(here, 'README.md')
with open(readme_file) as fp:
  long_description = fp.read()

setup(
  name='fortiel',

  description='Fortiel Compiler / Fortran Preprocessor',
  long_description=long_description,
  long_description_content_type='text/markdown',

  version='0.0.6',

  url='https://github.com/Jhuighuy/fortiel',

  author='Oleg Butakov',
  author_email='butakovoleg@gmail.com',

  license='MIT',

  classifiers=[
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
  ],

  keywords='fortran fortiel metaprogramming pre-processor',

  package_dir={'': 'src'},
  py_modules=['fortiel', 'gfortiel'],

  entry_points={
    'console_scripts': [
      'fortiel=fortiel:tielMain',
      'gfortiel=gfortiel:gfortielMain'
    ]
  }
)
