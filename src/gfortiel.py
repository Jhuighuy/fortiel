#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
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
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

import tempfile
import sys
import os
from typing import List, Tuple
from fortiel import tielPreprocess

_FORTRAN_EXT = [".f", ".for", ".f90", ".f03", ".f08"]


def _gfortielParseArguments() -> Tuple[List[str], List[str]]:
  '''Separate GNU Fortran options and input files.'''
  arguments: List[str] = []
  filePaths: List[str] = []
  for arg in sys.argv[1:]:
    isInputFile = \
      not (arg.startswith("-")
           or (len(arguments) > 0
               and arguments[-1] == "-o"))
    if isInputFile:
      ext = os.path.splitext(arg)[1]
      isInputFile = ext.lower() in _FORTRAN_EXT
    if isInputFile:
      filePaths.append(arg)
    else:
      arguments.append(arg)
  return arguments, filePaths


def _gfortielPreprocess(filePath: str,
                        outputFilePath: str) -> None:
  tielPreprocess(filePath, outputFilePath)


def gfortielMain() -> None:
  arguments, filePaths = _gfortielParseArguments()
  outputFilePaths = []
  for filePath in filePaths:
    outputFilePath \
      = tempfile.NamedTemporaryFile().name \
        + os.path.splitext(filePath)[1]
    outputFilePaths.append(outputFilePath)
    _gfortielPreprocess(filePath, outputFilePath)
  gfortranCommand = f'gfortran {" ".join(arguments)} {" ".join(outputFilePaths)}'
  gfortranExitCode = os.system(gfortranCommand)
  sys.exit(gfortranExitCode)


if __name__ == "__main__":
  gfortielMain()
