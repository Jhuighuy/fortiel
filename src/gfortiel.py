#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #
# +-+-+                                                       +-+-+ #
# +-+-+     ,------.               ,--.  ,--.       ,--.      +-+-+ #
# +-+-+     |  .---',---. ,--.--.,-'  '-.`--' ,---. |  |      +-+-+ #
# +-+-+     |  `--,| .-. ||  .--''-.  .-',--.| .-. :|  |      +-+-+ #
# +-+-+     |  |`  ' '-' '|  |     |  |  |  |\   --.|  |      +-+-+ #
# +-+-+     `--'    `---' `--'     `--'  `--' `----'`--'      +-+-+ #
# +-+-+                                                       +-+-+ #
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #
# +-+-+                                                       +-+-+ #
# +-+                                                           +-+ #
# +                                                               + #
#                                                                   #
# Copyright (C) 2021 Oleg Butakov                                   #
#                                                                   #
# Permission is hereby granted, free of charge, to any person       #
# obtaining a copy of this software and associated documentation    #
# files (the "Software"), to deal in the Software without           #
# restriction, including without limitation the rights  to use,     #
# copy, modify, merge, publish, distribute, sublicense, and/or      #
# sell copies of the Software, and to permit persons to whom the    #
# Software is furnished to do so, subject to the following          #
# conditions:                                                       #
#                                                                   #
# The above copyright notice and this permission notice shall be    #
# included in all copies or substantial portions of the Software.   #
#                                                                   #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,   #
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES   #
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND          #
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT       #
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,      #
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING      #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR     #
# OTHER DEALINGS IN THE SOFTWARE.                                   #
#                                                                   #
# +                                                               + #
# +-+                                                           +-+ #
# +-+-+                                                       +-+-+ #
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #

import sys
import os
import glob
import tempfile
from typing import List, Tuple
from fortiel import tielPreprocess, TielError


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_EXIT_SUCCESS = 0
_EXIT_ERROR = 1

_FORTRAN_EXT = [".f", ".for", ".f90", ".f03", ".f08"]


def _gfortielParseArguments() -> Tuple[List[str], List[str]]:
  """Parse GNU Fortran options and extract input files."""
  otherArgs: List[str] = []
  filePaths: List[str] = []
  for arg in sys.argv[1:]:
    isSourceFilePath = \
      not arg.startswith("-") \
           and (len(otherArgs) == 0 or otherArgs[-1] != "-o")
    if isSourceFilePath:
      ext = os.path.splitext(arg)[1]
      isSourceFilePath = ext.lower() in _FORTRAN_EXT
    # Append the argument or the file path.
    if isSourceFilePath:
      matchedPaths = glob.glob(arg)
      if matchedPaths:
        filePaths += matchedPaths
      else:
        filePaths.append(arg)
    else:
      otherArgs.append(arg)
  return otherArgs, filePaths


def _gfortielPreprocess(filePath: str,
                        outputFilePath: str) -> int:
  """Preprocess the source or output errors in GNU Fortran style."""
  try:
    tielPreprocess(filePath, outputFilePath)
    return _EXIT_SUCCESS
  except TielError as error:
    lineNumber, message = error.lineNumber, error.message
    errorMessage \
      = f'{filePath}:{lineNumber}:{1}:\n\n\nFatal Error: {message}'
    print(errorMessage, file=sys.stderr, flush=True)
    return _EXIT_ERROR


def main() -> None:
  """GNU Fortiel compiler entry point."""
  otherArgs, filePaths = _gfortielParseArguments()
  # Preprocess the sources.
  exitCode = 0
  outputFilePaths = []
  for filePath in filePaths:
    with tempfile.NamedTemporaryFile() as outputFile:
      outputFilePath \
        = outputFile.name + os.path.splitext(filePath)[1]
    fileExitCode = _gfortielPreprocess(filePath, outputFilePath)
    if fileExitCode == _EXIT_SUCCESS:
      outputFilePaths.append(outputFilePath)
    exitCode |= fileExitCode
  # Compile the preprocessed sources.
  if exitCode == _EXIT_SUCCESS:
    compilerCommand \
      = f'gfortran {" ".join(otherArgs)} {" ".join(outputFilePaths)}'
    exitCode = os.system(compilerCommand)
    sys.stderr.flush()
  # Delete the generated preprocessed sources and exit.
  try:
    for outputFilePath in outputFilePaths:
      os.remove(outputFilePath)
  finally:
    sys.exit(exitCode)


if __name__ == "__main__":
  main()
