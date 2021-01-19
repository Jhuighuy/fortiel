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
from fortiel import TielError, tiel_preprocess


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_EXIT_SUCCESS = 0
_EXIT_ERROR = 1

_FORTRAN_EXT = [
    ".f", ".for",
    ".f90", ".f03", ".f08"
]


def _gfortiel_parse_arguments() -> Tuple[List[str], List[str]]:
    """Parse GNU Fortran options and extract input files."""
    other_args: List[str] = []
    file_paths: List[str] = []
    for arg in sys.argv[1:]:
        is_source_file_path = \
            not (arg.startswith("-")
                 or (len(other_args) > 0 and other_args[-1] == "-o"))
        if is_source_file_path:
            ext = os.path.splitext(arg)[1]
            is_source_file_path = ext.lower() in _FORTRAN_EXT
        # Append the argument or the file path.
        if is_source_file_path:
            matched_paths = glob.glob(arg)
            file_paths += matched_paths
        else:
            other_args.append(arg)
    return other_args, file_paths


def _gfortiel_preprocess(file_path: str,
                         output_file_path: str) -> int:
    """Preprocess the source or output errors in GNU Fortran style."""
    try:
        tiel_preprocess(file_path, output_file_path)
        return _EXIT_SUCCESS
    except TielError as error:
        line_number, message = error.line_number, error.message
        gfortran_message \
            = f'{file_path}:{line_number}:{1}:\n\n\nFatal Error: {message}'
        print(gfortran_message, file=sys.stderr, flush=True)
        return _EXIT_ERROR


def gfortiel_main() -> None:
    """
    GNU Fortiel compiler entry point.
    :return:
    """
    other_args, file_paths = _gfortiel_parse_arguments()
    # Preprocess the sources.
    exit_code = 0
    output_file_paths = []
    for file_path in file_paths:
        output_file_path \
            = tempfile.NamedTemporaryFile().name + os.path.splitext(file_path)[1]
        output_file_paths.append(output_file_path)
        exit_code |= _gfortiel_preprocess(file_path, output_file_path)
    # Compile the preprocessed sources.
    if exit_code == _EXIT_SUCCESS:
        compiler_command \
            = f'gfortran {" ".join(other_args)} {" ".join(output_file_paths)}'
        exit_code |= os.system(compiler_command)
    # Delete the generated preprocessed sources and exit.
    for output_file_path in output_file_paths:
        os.remove(output_file_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    gfortiel_main()
