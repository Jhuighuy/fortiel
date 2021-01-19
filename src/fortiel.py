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


"""
Fortiel preprocessor.
"""

import re
from os import path
import argparse
from typing import Any, List, Dict, \
    Callable, Optional, Pattern, Match


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielOptions:
    """
    Preprocessor options.
    """

    def __init__(self) -> None:
        self.include_paths: List[str] = []


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielError(Exception):
    """
    Preprocessor syntax tree parse error.
    """

    def __init__(self, message: str, file_path: str, line_number: int) -> None:
        super().__init__()
        self.message: str = message
        self.file_path: str = file_path
        self.line_number: int = line_number

    def __str__(self) -> str:
        message \
            = f'{self.file_path}:{self.line_number}:1:\n\n' \
            + f'Fatal Error: {self.message}'
        return message


class TielDirError(TielError):
    """
    Unexpected directive preprocessor error.
    """


class TielEvalError(TielError):
    """
    Error in the directive or line substitution evaluation.
    """


class TielFileError(TielEvalError):
    """
    Error in the include file path.
    """


class TielTypeError(TielError):
    """
    Type error in the expression.
    """


class TielEndError(TielError):
    """
    Unexpected end of file preprocessor error.
    """

    def __init__(self, file_path: str, line_number: int):
        super().__init__('unexpected end of file', file_path, line_number)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielTree:
    """Preprocessor syntax tree.
    """

    def __init__(self, file_path: str) -> None:
        self.file_path: str = file_path
        self.root_nodes: List[TielNode] = []


class TielNode:
    """Preprocessor syntax tree node.
    """

    def __init__(self, file_path: str, line_number: int) -> None:
        self.file_path: str = file_path
        self.line_number: int = line_number


class TielNodeLineList(TielNode):
    """The list of code lines syntax tree node.
    """

    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.lines: List[str] = []


class TielNodeUse(TielNode):
    """The USE/INCLUDE directive syntax tree node.
    """

    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.include_file_path: str = ''
        self.do_print_lines: bool = False


class TielNodeLet(TielNode):
    """The LET directive syntax tree node.
    """

    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.name: str = ''
        self.arguments: Optional[str] = None
        self.expression: str = ''


class TielNodeDel(TielNode):
    """The DEL directive syntax tree node.
    """

    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.names: List[str] = []


class TielNodeIfEnd(TielNode):
    """The IF/ELSE IF/ELSE/END IF directive syntax tree node.
    """

    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.cond_expr: str = ''
        self.then_nodes: List[TielNode] = []
        self.else_if_nodes: List[TielNodeElseIf] = []
        self.else_nodes: List[TielNode] = []


class TielNodeElseIf(TielNode):
    """The ELSE IF directive syntax tree node.
    """

    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.cond_expr: str = ''
        self.nodes: List[TielNode] = []


class TielNodeDoEnd(TielNode):
    """The DO/END DO directive syntax tree node.
    """

    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.index_name: str = ''
        self.bounds_expr: str = ''
        self.nodes: List[TielNode] = []


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def _reg_expr(pattern: str) -> Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


_DIR = _reg_expr(r'^\s*#fpp(?:\s+(?P<dir>.*))?$')
_DIR_HEAD = _reg_expr(r'^(?P<head>[^\s]+)(?:\s+(?P<head2>[^\s]+))?')

_USE = _reg_expr(r'^(?P<dir>use|include)\s+'
                 + r'(?P<path>(?:\".+\")|(?:\'.+\')|(?:\<.+\>))$')

_LET = _reg_expr(r'^let\s+(?P<name>[a-zA-Z]\w*)\s*'
                 + r'(?P<args>\((?:\*?\*?[a-zA-Z]\w*(?:\s*,\s*\*?\*?[a-zA-Z]\w*)*)?\s*\))?\s*'
                 + r'=\s*(?P<expr>.*)$')

_DEL = _reg_expr(r'^undef\s+(?P<names>[a-zA-Z]\w*(?:\s*,\s*[a-zA-Z]\w*)*)$')

_IF = _reg_expr(r'^if\s*(?P<cond>.+)$')
_ELSE_IF = _reg_expr(r'^else\s*if\s*(?P<cond>.+)$')
_ELSE = _reg_expr(r'^else$')
_END_IF = _reg_expr(r'^end\s*if$')

_DO = _reg_expr(r'^do\s+(?P<index>[a-zA-Z]\w*)\s*=\s*(?P<bounds>.*)$')
_END_DO = _reg_expr(r'^end\s*do$')

_LINE = _reg_expr(r'(line)?\s*(?P<num>\d+)\s+(?P<path>(\'.+\')|(\".+\"))')


class TielParser:
    """Preprocessor syntax tree parser.
    """

    def __init__(self,
                 file_path: str, lines: List[str]) -> None:
        self._file_path: str = file_path
        self._lines: List[str] = lines
        self._cur_line: str = self._lines[0]
        self._cur_line_index: int = 0
        self._cur_line_number: int = 1

    def _matches_end(self) -> bool:
        return self._cur_line_index >= len(self._lines)

    def _advance_line(self) -> None:
        self._cur_line_index += 1
        self._cur_line_number += 1
        self._cur_line: str = \
            '' if self._matches_end() else self._lines[self._cur_line_index].rstrip()

    def _matches_line(self, *reg_expr_list: Pattern[str]) -> Optional[Match[str]]:
        if self._matches_end():
            raise TielEndError(self._file_path, self._cur_line_number)
        for reg_expr in reg_expr_list:
            match = reg_expr.match(self._cur_line)
            if match is not None:
                return match
        return None

    def _parse_line_cont(self) -> None:
        """Parse continuation lines."""
        while self._cur_line.endswith('&'):
            self._cur_line: str = self._cur_line[:-1] + ' '
            self._cur_line_index += 1
            self._cur_line_number += 1
            if self._matches_end():
                raise TielEndError(self._file_path, self._cur_line_number)
            next_line = self._lines[self._cur_line_index].lstrip()
            if next_line.startswith('!'):
                continue
            if next_line.startswith('&'):
                next_line = next_line[1:].lstrip()
            self._cur_line += next_line.rstrip()

    @staticmethod
    def _parse_head(directive: Optional[str]) -> Optional[str]:
        # Empty directives does not have a head.
        if directive is None or directive == '':
            return None
        # ELSE is merged with IF,
        # END is merged with any following word.
        dir_head, dir_head2 \
            = _DIR_HEAD.match(directive).group('head', 'head2')
        dir_head = dir_head.lower()
        if dir_head2 is not None:
            dir_head2 = dir_head2.lower()
            if dir_head == 'end' or dir_head == 'else' and dir_head2 == 'if':
                dir_head += dir_head2
        return dir_head

    def _matches_dir_head(self, *dir_head_list: str) -> Optional[str]:
        self._parse_line_cont()
        dir_match = self._matches_line(_DIR)
        if dir_match is not None:
            directive = dir_match['dir'].lower()
            dir_head = type(self)._parse_head(directive)
            if dir_head in dir_head_list:
                return dir_head
        return None

    def _match_directive(self, reg_exp: Pattern[str]) -> Match[str]:
        directive = self._matches_line(_DIR).group('dir').rstrip()
        match = reg_exp.match(directive)
        if match is None:
            dir_head = type(self)._parse_head(directive)
            message = f'invalid <{dir_head}> directive syntax'
            raise TielDirError(message, self._file_path, self._cur_line_number)
        self._advance_line()
        return match

    def parse(self) -> TielTree:
        """Parse the source lines."""
        tree = TielTree(self._file_path)
        while not self._matches_end():
            tree.root_nodes.append(self._parse_single())
        return tree

    def _parse_single(self) -> TielNode:
        """Parse a directive or a line block."""
        if self._matches_line(_DIR):
            return self._parse_directive()
        return self._parse_line_list()

    def _parse_line_list(self) -> TielNodeLineList:
        """Parse a line list."""
        node = TielNodeLineList(self._file_path,
                                self._cur_line_number)
        while True:
            node.lines.append(self._cur_line)
            self._advance_line()
            if self._matches_end() or self._matches_line(_DIR):
                break
        return node

    def _parse_directive(self) -> TielNode:
        """Parse a directive."""
        self._parse_line_cont()
        directive = self._matches_line(_DIR)['dir']
        dir_head = type(self)._parse_head(directive)
        if dir_head in ['use', 'include']:
            return self._parse_directive_use()
        if dir_head == 'let':
            return self._parse_directive_let()
        if dir_head == 'del':
            return self._parse_directive_del()
        if dir_head == 'if':
            return self._parse_directive_if_end()
        if dir_head == 'do':
            return self._parse_directive_do_end()
        if dir_head == 'line' \
                or (dir_head is not None and dir_head.isdecimal()):
            self._parse_directive_line()
            return self._parse_single()
        # Determine the error type:
        # either the known directive is misplaced,
        # either the directive is unknown.
        if dir_head is None:
            message = f'empty directive'
            raise TielDirError(message, self._file_path, self._cur_line_number)
        elif dir_head in ['else', 'elseif', 'endif', 'enddo']:
            message = f'misplaced directive <{dir_head}>'
            raise TielDirError(message, self._file_path, self._cur_line_number)
        else:
            message = f'unknown or mistyped directive <{dir_head}>'
            raise TielDirError(message, self._file_path, self._cur_line_number)

    def _parse_directive_use(self) -> TielNodeUse:
        """Parse USE/INCLUDE directives."""
        node = TielNodeUse(self._file_path,
                           self._cur_line_number)
        directive, node.include_file_path \
            = self._match_directive(_USE).group('dir', 'path')
        node.include_file_path = node.include_file_path[1:-1]
        if directive.lower() == 'include':
            node.do_print_lines = True
        return node

    def _parse_directive_let(self) -> TielNodeLet:
        """Parse LET directive."""
        # Note that we are not
        # evaluating or validating define arguments and body here.
        node = TielNodeLet(self._file_path,
                           self._cur_line_number)
        node.name, node.arguments, node.expression \
            = self._match_directive(_LET).group('name', 'args', 'expr')
        if node.arguments is not None:
            node.arguments = node.arguments[1:-1].strip()
        return node

    def _parse_directive_del(self) -> TielNodeDel:
        """Parse DEL directive."""
        # Note that we are not
        # evaluating or validating define name here.
        node = TielNodeDel(self._file_path,
                           self._cur_line_number)
        names = self._match_directive(_DEL).group('names')
        node.names = [name.strip() for name in names.split(',')]
        return node

    def _parse_directive_if_end(self) -> TielNodeIfEnd:
        """Parse IF/ELSE IF/ELSE/END IF directives."""
        # Note that we are not
        # evaluating or validating conditions here.
        node = TielNodeIfEnd(self._file_path,
                             self._cur_line_number)
        node.cond_expr = self._match_directive(_IF)['cond']
        while not self._matches_dir_head('elseif', 'else', 'endif'):
            node.then_nodes.append(self._parse_single())
        if self._matches_dir_head('elseif'):
            while not self._matches_dir_head('else', 'endif'):
                else_if_node = TielNodeElseIf(self._file_path,
                                              self._cur_line_number)
                else_if_node.cond_expr = self._match_directive(_ELSE_IF)['cond']
                while not self._matches_dir_head('elseif', 'else', 'endif'):
                    else_if_node.nodes.append(self._parse_single())
                node.else_if_nodes.append(else_if_node)
        if self._matches_dir_head('else'):
            self._match_directive(_ELSE)
            while not self._matches_dir_head('endif'):
                node.else_nodes.append(self._parse_single())
        self._match_directive(_END_IF)
        return node

    def _parse_directive_do_end(self) -> TielNodeDoEnd:
        """Parse DO/END DO directives."""
        # Note that we are not
        # evaluating or validating loop bounds here.
        node = TielNodeDoEnd(self._file_path,
                             self._cur_line_number)
        node.index_name, node.bounds_expr \
            = self._match_directive(_DO).group('index', 'bounds')
        while not self._matches_dir_head('enddo'):
            node.nodes.append(self._parse_single())
        self._match_directive(_END_DO)
        return node

    def _parse_directive_line(self) -> None:
        """Parse LINE directive."""
        self._file_path, self._cur_line_number \
            = self._match_directive(_LINE).group('path', 'num')
        self._file_path = self._file_path[1:-1]
        self._cur_line_number = int(self._cur_line_number)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_BUILTIN_NAMES = [
    '__FILE__', '__LINE__',
    '__DATE__', '__TIME__',
    '__INDEX__',
]


class TielEvaluator:
    """Preprocessor syntax tree evaluator.
    """

    def __init__(self, options: TielOptions):
        self._scope: Dict[str, Any] = {}
        self._options: TielOptions = options

    def eval_tree(self,
                  tree: TielTree,
                  print_func: Callable[[str], None]) -> None:
        """Evaluate the syntax tree or the syntax tree node."""
        self._eval_node_list(tree.root_nodes, print_func)

    def _eval_node_list(self,
                        nodes: List[TielNode],
                        print_func: Callable[[str], None]) -> None:
        """Evaluate the syntax tree node or a list of nodes."""
        for node in nodes:
            if isinstance(node, TielNodeLineList):
                self._eval_line_list(node, print_func)
            else:
                self._eval_directive(node, print_func)

    def _eval_python_expr(self,
                          expression: str,
                          file_path: str, line_number: int) -> Any:
        """Evaluate Python expression."""
        try:
            value = eval(expression, self._scope)
            return value
        except Exception as error:
            message = 'Python expression evaluation error: ' \
                      + f'{str(error).replace("<string>", f"expression `{expression}`")}'
            raise TielEvalError(message, file_path, line_number) from error

    def _eval_line(self,
                   line: str,
                   file_path: str, line_number: int,
                   print_func: Callable[[str], None]) -> None:
        """Evaluate in-line substitutions."""
        # Evaluate expression substitutions.
        def _line_sub(match: Match[str]) -> str:
            expression = match['expr']
            return str(self._eval_python_expr(expression, file_path, line_number))
        line = re.sub(r'`(?P<expr>.+)`', _line_sub, line)

        # Evaluate <@:> substitutions.
        def _loop_sub(match: Match[str]) -> str:
            expression = match['expr']
            index = self._scope.get('__INDEX__')
            if index is None:
                message = '<@:> substitution outside of the <do> loop body'
                raise TielEvalError(message, file_path, line_number)
            return str(index * expression)
        line = re.sub(r'@(?P<expr>:(\s*,)?)', _loop_sub, line)
        print_func(line)

    def _eval_line_list(self,
                        node: TielNodeLineList,
                        print_func: Callable[[str], None]) -> None:
        """Evaluate line block."""
        print_func(f'# {node.line_number} "{node.file_path}"')
        for line_number, line in \
                enumerate(node.lines, start=node.line_number):
            self._eval_line(line, node.file_path, line_number, print_func)

    def _eval_directive(self,
                        node: TielNode,
                        print_func: Callable[[str], None]):
        """Evaluate directive."""
        if isinstance(node, TielNodeUse):
            return self._eval_directive_use(node, print_func)
        if isinstance(node, TielNodeLet):
            return self._eval_directive_let(node)
        if isinstance(node, TielNodeDel):
            return self._eval_directive_del(node)
        if isinstance(node, TielNodeIfEnd):
            return self._eval_directive_if_end(node, print_func)
        if isinstance(node, TielNodeDoEnd):
            return self._eval_directive_do_end(node, print_func)
        node_type = node.__class__.__name__
        raise RuntimeError(f'no evaluator for directive type {node_type}')

    @staticmethod
    def _find_file(file_path: str,
                   dir_paths: List[str]) -> Optional[str]:
        file_path = path.expanduser(file_path)
        if path.exists(file_path):
            return file_path
        for dir_path in dir_paths:
            file_path_in_dir = path.expanduser(path.join(dir_path, file_path))
            if path.exists(file_path_in_dir):
                return file_path_in_dir
        return None

    def _eval_directive_use(self,
                            node: TielNodeUse,
                            print_func: Callable[[str], None]) -> None:
        """Evaluate USE/INCLUDE directive."""
        cur_dir_path, _ = path.split(node.file_path)
        header_file_path \
            = type(self)._find_file(node.include_file_path,
                                    self._options.include_paths + [cur_dir_path])
        if header_file_path is None:
            message = f'`{node.include_file_path}` was not found in the include paths'
            raise TielFileError(message, node.file_path, node.line_number)
        try:
            with open(header_file_path, mode='r') as fp:
                header_lines = fp.read().splitlines()
        except IsADirectoryError as error:
            message = f'`{node.include_file_path}` is a directory, file expected'
            raise TielFileError(message, node.file_path, node.line_number) from error
        header_tree = TielParser(node.include_file_path, header_lines).parse()
        if node.do_print_lines:
            self.eval_tree(header_tree, print_func)
        else:
            self.eval_tree(header_tree, lambda _: None)

    def _eval_directive_let(self,
                            node: TielNodeLet) -> None:
        """Evaluate LET directive."""
        if node.name in self._scope:
            message = f'name `{node.name}` is already defined.'
            raise TielEvalError(message, node.file_path, node.line_number)
        if node.name in _BUILTIN_NAMES:
            message = f'builtin name <{node.name}> can not be redefined'
            raise TielEvalError(message, node.file_path, node.line_number)
        if node.arguments is None:
            value = self._eval_python_expr(node.expression,
                                           node.file_path, node.line_number)
            self._scope[node.name] = value
        else:
            arg_names = [arg.strip() for arg in node.arguments.split(',')]
            if len(arg_names) > len(set(arg_names)):
                message = 'functional <let> arguments must be unique'
                raise TielEvalError(message, node.file_path, node.line_number)
            # Evaluate functional LET as lambda function.
            expression = f'lambda {node.arguments}: {node.expression}'
            func = self._eval_python_expr(expression,
                                          node.file_path, node.line_number)
            self._scope[node.name] = func

    def _eval_directive_del(self,
                            node: TielNodeDel) -> None:
        """Evaluate DEL directive."""
        for name in node.names:
            if name not in self._scope:
                message = f'name `{name}` was not previously defined'
                raise TielEvalError(message, node.file_path, node.line_number)
            if name in _BUILTIN_NAMES:
                message = f'builtin name <{name}> can not be undefined'
                raise TielEvalError(message, node.file_path, node.line_number)
            del self._scope[name]

    def _eval_directive_if_end(self,
                               node: TielNodeIfEnd,
                               print_func: Callable[[str], None]) -> None:
        """Evaluate IF/ELSE IF/ELSE/END IF node."""
        if self._eval_python_expr(
                node.cond_expr,
                node.file_path, node.line_number):
            self._eval_node_list(node.then_nodes, print_func)
        else:
            for elseIfNode in node.else_if_nodes:
                if self._eval_python_expr(
                        elseIfNode.cond_expr,
                        elseIfNode.file_path, elseIfNode.line_number):
                    self._eval_node_list(elseIfNode.nodes, print_func)
                    break
            else:
                self._eval_node_list(node.else_nodes, print_func)

    def _eval_directive_do_end(self,
                               node: TielNodeDoEnd,
                               print_func: Callable[[str], None]) -> None:
        """Evaluate DO/END DO node."""
        bounds = self._eval_python_expr(node.bounds_expr,
                                        node.file_path, node.line_number)
        if not isinstance(bounds, tuple) \
                or not (2 <= len(bounds) <= 3) \
                or list(map(type, bounds)) != len(bounds) * [int]:
            message \
                = 'tuple of two or three integers inside the <do> ' \
                + f' directive bounds is expected, got `{node.bounds_expr}`'
            raise TielEvalError(message, node.file_path, node.line_number)
        start, stop = bounds[0:2]
        step = bounds[2] if len(bounds) == 3 else 1
        # Save and restore previous index value
        # in case we are inside the nested loop.
        prev_index = self._scope.get('__INDEX__')
        for index in range(start, stop + 1, step):
            self._scope[node.index_name] = index
            self._scope['__INDEX__'] = index
            self._eval_node_list(node.nodes, print_func)
        del self._scope[node.index_name]
        if prev_index is not None:
            self._scope['__INDEX__'] = prev_index
        else:
            del self._scope['__INDEX__']


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tiel_preprocess(file_path: str,
                    output_file_path: str,
                    options: TielOptions = TielOptions()) -> None:
    """Preprocess the source file."""
    with open(file_path, 'r') as fp:
        lines = fp.read().splitlines()
    tree = TielParser(file_path, lines).parse()
    with open(output_file_path, 'w') as fp:
        def _print_func(line): print(line, file=fp)
        TielEvaluator(options).eval_tree(tree, _print_func)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tiel_main() -> None:
    """Fortiel entry point."""
    arg_parser = \
        argparse.ArgumentParser(prog='fortiel')
    arg_parser.add_argument(
        '-D', '--define',
        action='append', dest='defines', metavar='NAME[=VALUE]',
        help='define a named variable')
    arg_parser.add_argument(
        '-I', '--include',
        action='append', dest='defines', metavar='INCLUDE_DIR',
        help='add an include directory path')
    arg_parser.add_argument(
        '-N', '--line_markers',
        choices=['fpp', 'cpp', 'node'], default='fpp',
        help='emit line markers in the output')
    arg_parser.add_argument('file_path',
                            help='input file path')
    arg_parser.add_argument('output_file_path',
                            help='output file path')
    args = arg_parser.parse_args()
    file_path = args.file_path
    output_file_path = args.output_file_path
    tiel_preprocess(file_path, output_file_path)


if __name__ == '__main__':
    tiel_main()
