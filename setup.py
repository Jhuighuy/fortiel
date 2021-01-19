# -*- coding: utf-8 -*-
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
#
# ,------.               ,--.  ,--.       ,--.
# |  .---',---. ,--.--.,-'  '-.`--' ,---. |  |
# |  `--,| .-. ||  .--''-.  .-',--.| .-. :|  |
# |  |`  ' '-' '|  |     |  |  |  |\   --.|  |
# `--'    `---' `--'     `--'  `--' `----'`--'
#
# Copyright (C) 2021 Oleg Butakov
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights  to use,
# copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #

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

    version='0.0.12',

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
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    keywords='fortran fortiel metaprogramming pre-processor',

    package_dir={'': 'src'},
    py_modules=['fortiel', 'gfortiel'],

    entry_points={
        'console_scripts': [
            'fortiel=fortiel:tiel_main',
            'gfortiel=gfortiel:gfortiel_main'
        ]
    }
)
