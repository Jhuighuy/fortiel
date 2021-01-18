#!/usr/bin/env python3
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


import sys
import os
import glob
import tempfile
from typing import List, Tuple
from fortiel import TielError, tielPreprocess


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_EXIT_SUCCESS = 0
_EXIT_ERROR = 1

_FORTRAN_EXT = [
  ".f", ".for",
  ".f90", ".f03", ".f08"
]


def _gfortielParseArguments() -> Tuple[List[str], List[str]]:
  '''Separate GNU Fortran options and input files.'''
  otherArgs: List[str] = []
  filePaths: List[str] = []
  for arg in sys.argv[1:]:
    isSourceFilePath = \
      not (arg.startswith("-")
           or (len(otherArgs) > 0 and otherArgs[-1] == "-o"))
    if isSourceFilePath:
      ext = os.path.splitext(arg)[1]
      isSourceFilePath = ext.lower() in _FORTRAN_EXT
    # Append the argument or the file path.
    if isSourceFilePath:
      matchedPaths = glob.glob(arg)
      filePaths += matchedPaths
    else:
      otherArgs.append(arg)
  return otherArgs, filePaths


def _gfortielPreprocess(filePath: str,
                        outputFilePath: str) -> int:
  '''Preprocess the source or output errors in GNU Fortran style.'''
  try:
    tielPreprocess(filePath, outputFilePath)
    return _EXIT_SUCCESS
  except TielError as error:
    lineNumber, message = error.lineNumber, error.message
    gfortranMessage \
      = f'{filePath}:{lineNumber}:{1}:\n\n\nFatal Error: {message}'
    print(gfortranMessage, file=sys.stderr)
    sys.stderr.flush()
    return _EXIT_ERROR


def gfortielMain() -> None:
  otherArgs, filePaths = _gfortielParseArguments()
  # Preprocess the sources.
  exitCode = 0
  outputFilePaths = []
  for filePath in filePaths:
    outputFilePath \
      = tempfile.NamedTemporaryFile().name + os.path.splitext(filePath)[1]
    outputFilePaths.append(outputFilePath)
    exitCode |= _gfortielPreprocess(filePath, outputFilePath)
  # Compile the preprocessed sources.
  if exitCode == _EXIT_SUCCESS:
    compilerCommand = f'gfortran {" ".join(otherArgs)} {" ".join(outputFilePaths)}'
    exitCode |= os.system(compilerCommand)
  # Delete the generated preprocessed sources and exit.
  for outputFilePath in outputFilePaths:
    os.remove(outputFilePath)
  sys.exit(exitCode)


if __name__ == "__main__":
  gfortielMain()
