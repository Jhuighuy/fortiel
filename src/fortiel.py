#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines, eval-used

# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=                                                       =-=-=-=-= #
# =-=-=-=-=     ,------.               ,--.  ,--.       ,--.      =-=-=-=-= #
# =-=-=-=-=     |  .---',---. ,--.--.,-'  '-.`--' ,---. |  |      =-=-=-=-= #
# =-=-=-=-=     |  `--,| .-. ||  .--''-.  .-',--.| .-. :|  |      =-=-=-=-= #
# =-=-=-=-=     |  |`  ' '-' '|  |     |  |  |  |\   --.|  |      =-=-=-=-= #
# =-=-=-=-=     `--'    `---' `--'     `--'  `--' `----'`--'      =-=-=-=-= #
# =-=-=-=-=                                                       =-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=                                                       =-=-=-=-= #
# =-=                                                                   =-= #
# =                                                                       = #
#                                                                           #
# Copyright (C) 2021 Oleg Butakov                                           #
#                                                                           #
# Permission is hereby granted, free of charge, to any person obtaining a   #
# copy of this software and associated documentation files                  #
# (the "Software"), to deal in the Software without restriction, including  #
# without limitation the rights  to use, copy, modify, merge, publish,      #
# distribute, sublicense, and/or sell copies of the Software, and to permit #
# persons to whom the Software is furnished to do so, subject to the        #
# following conditions:                                                     #
#                                                                           #
# The above copyright notice and this permission notice shall be included   #
# in all copies or substantial portions of the Software.                    #
#                                                                           #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS   #
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF                #
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.    #
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY      #
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,      #
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE         #
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                    #
#                                                                           #
# =                                                                       = #
# =-=                                                                   =-= #
# =-=-=-=-=                                                       =-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


"""
Fortiel language translator and executor.
"""

import re
import argparse
from os import path

from typing import (cast, final,
                    List, Set, Dict, Tuple, Any, Union,
                    Optional, Callable, Literal, Pattern, Match)


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=                Fortiel Helper Routines                =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


def _reg_expr(pattern: str) -> Pattern[str]:
    """Compile regular expression."""
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.VERBOSE)


def _make_name(name: str) -> str:
    """Compile a single-word lower case identifier."""
    return re.sub(r'\s*', '', name.lower())


def _find_file(file_path: str, dir_paths: List[str]) -> Optional[str]:
    """Find file in the directory list."""
    file_path = path.expanduser(file_path)
    if path.exists(file_path):
        return path.abspath(file_path)
    for dir_path in dir_paths:
        rel_file_path = path.expanduser(path.join(dir_path, file_path))
        if path.exists(rel_file_path):
            return path.abspath(rel_file_path)
    here = path.abspath(path.dirname(__file__))
    rel_file_path = path.join(here, file_path)
    if path.exists(rel_file_path):
        return rel_file_path
    return None


def _find_duplicate(strings: List[str]) -> Optional[str]:
    """Find first duplicate in the list."""
    strings_set: Set[str] = set()
    for string in strings:
        if string in strings_set:
            return string
        strings_set.add(string)
    return None


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=            Fortiel Exceptions and Messages            =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


class FortielError(Exception):
    """Fortiel compilation/execution error."""
    def __init__(self, message: str, file_path: str, line_number: int) -> None:
        super().__init__()
        self.message: str = message
        self.file_path: str = file_path
        self.line_number: int = line_number

    def __str__(self) -> str:
        # Format matched GFortran error messages.
        return f'{self.file_path}:{self.line_number}:1:\n\nFatal Error: {self.message}'


@final
class FortielGrammarError(FortielError):
    """Fortiel grammar error."""
    def __init__(self, message: str, file_path: str, line_number: int) -> None:
        super().__init__(
            f'Fortiel syntax error: {message}', file_path, line_number)


@final
class FortielSyntaxError(FortielError):
    """Fortiel syntax error."""
    def __init__(self, message: str, file_path: str, line_number: int) -> None:
        super().__init__(
            f'Fortiel syntax error: {message}', file_path, line_number)


@final
class FortielRuntimeError(FortielError):
    """Fortiel runtime error."""
    def __init__(self, message: str, file_path: str, line_number: int) -> None:
        super().__init__(
            f'Fortiel runtime error: {message}', file_path, line_number)


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=                    Fortiel Options                    =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


@final
class FortielOptions:
    """Preprocessor options."""
    def __init__(self) -> None:
        self.defines: List[str] = []
        self.include_paths: List[str] = []
        self.line_marker_format: Literal['fpp', 'cpp', 'none'] = 'fpp'


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=         Fortiel Scanner and Directives Parser         =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


@final
class FortielTree:
    """Fortiel syntax tree."""
    def __init__(self, file_path: str) -> None:
        self.file_path: str = file_path
        self.root_nodes: List[FortielNode] = []


class FortielNode:
    """Fortiel syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        self.file_path: str = file_path
        self.line_number: int = line_number


@final
class FortielNodeLineList(FortielNode):
    """The list of code lines syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.lines: List[str] = []


@final
class FortielNodeUse(FortielNode):
    """The USE directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.imported_file_path: str = ''


@final
class FortielNodeLet(FortielNode):
    """The LET directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.name: str = ''
        self.arguments: Union[str, List[str], None] = None
        self.expression: str = ''


@final
class FortielNodeDefine(FortielNode):
    """The DEFINE directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.name: str = ''
        self.segment: str = ''


@final
class FortielNodeDel(FortielNode):
    """The DEL directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.names: List[str] = []


@final
class FortielNodeIf(FortielNode):
    """The IF/ELSE IF/ELSE/END IF directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.condition: str = ''
        self.then_nodes: List[FortielNode] = []
        self.elif_nodes: List[FortielNodeElseIf] = []
        self.else_nodes: List[FortielNode] = []


@final
class FortielNodeElseIf(FortielNode):
    """The ELSE IF directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.condition: str = ''
        self.then_nodes: List[FortielNode] = []


@final
class FortielNodeDo(FortielNode):
    """The DO/END DO directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.index_name: str = ''
        self.ranges: str = ''
        self.loop_nodes: List[FortielNode] = []


@final
class FortielNodeFor(FortielNode):
    """The FOR/END FOR directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.index_names: Union[str, List[str], None] = None
        self.ranges_expression: str = ''
        self.loop_nodes: List[FortielNode] = []


@final
class FortielNodeMacro(FortielNode):
    """The MACRO/END MACRO directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.name: str = ''
        self.pattern_nodes: List[FortielNodePattern] = []
        self.section_nodes: List[FortielNodeSection] = []
        self.finally_nodes: List[FortielNode] = []

    def construct(self) -> bool:
        """Is current macro a construct."""
        return len(self.section_nodes) > 0 or len(self.finally_nodes) > 0

    def section_names(self) -> List[str]:
        """Get a list of the section names."""
        return [node.name for node in self.section_nodes]


@final
class FortielNodeSection(FortielNode):
    """The SECTION directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.name: str = ''
        self.once: bool = False
        self.pattern_nodes: List[FortielNodePattern] = []


@final
class FortielNodePattern(FortielNode):
    """The PATTERN directive syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.pattern: Union[str, Pattern[str]] = ''
        self.match_nodes: List[FortielNode] = []


@final
class FortielNodeCallSegment(FortielNode):
    """The call segment syntax tree node."""
    def __init__(self, file_path: str, line_number: int) -> None:
        super().__init__(file_path, line_number)
        self.spaces: str = ''
        self.name: str = ''
        self.argument: str = ''


@final
class FortielNodeCall(FortielNode):
    """The call directive syntax tree node."""
    def __init__(self, node: FortielNodeCallSegment) -> None:
        super().__init__(node.file_path, node.line_number)
        self.spaces: str = node.spaces
        self.name: str = node.name
        self.argument: str = node.argument
        self.captured_nodes: List[FortielNode] = []
        self.call_section_nodes: List[FortielNodeCallSection] = []


@final
class FortielNodeCallSection(FortielNode):
    """The call directive section syntax tree node."""
    def __init__(self, node: FortielNodeCallSegment) -> None:
        super().__init__(node.file_path, node.line_number)
        self.name: str = node.name
        self.argument: str = node.argument
        self.captured_nodes: List[FortielNode] = []


_FORTIEL_DIRECTIVE = _reg_expr(r'^\s*\#[@$]\s*(?P<directive>.*)?$')
_DIR_HEAD = _reg_expr(r'^(?P<word>[^\s]+)(?:\s+(?P<word2>[^\s]+))?')

_FORTIEL_CALL = _reg_expr(
    r'''^(?P<spaces>\s*)
    \@(?P<name>(?:END\s*|ELSE\s*)?[A-Z]\w*)\b(?P<argument>[^!]*)(\s*!.*)?$''')

_FORTIEL_USE = _reg_expr(
    r'^USE\s+(?P<path>(?:\"[^\"]+\")|(?:\'[^\']+\')|(?:\<[^\>]+\>))$')

_FORTIEL_LET = _reg_expr(
    r'''^LET\s+(?P<name>[A-Z_]\w*)\s*
    (?P<arguments>
      \((?:\*{0,2}[A-Z_]\w*(?:\s*,\s*\*{0,2}[A-Z_]\w*)*)?\s*\))?\s*
    =\s*(?P<expression>.*)$''')

_FORTIEL_DEFINE = _reg_expr(r'^DEFINE\s+(?P<name>[A-Z_]\w*)\s+(?P<segment>.*)$')
_FORTIEL_DEL = _reg_expr(r'^DEL\s+(?P<names>[A-Z_]\w*(?:\s*,\s*[A-Z_]\w*)*)$')

_FORTIEL_IF = _reg_expr(r'^IF\s*(?P<condition>.+)$')
_FORTIEL_ELSE_IF = _reg_expr(r'^ELSE\s*IF\s*(?P<condition>.+)$')
_FORTIEL_ELSE = _reg_expr(r'^ELSE$')
_FORTIEL_END_IF = _reg_expr(r'^END\s*IF$')

_FORTIEL_DO = _reg_expr(r'^DO\s+(?P<index_name>[A-Z_]\w*)\s*=\s*(?P<ranges>.*)$')
_FORTIEL_END_DO = _reg_expr(r'^END\s*DO$')

_FORTIEL_FOR = _reg_expr(
    r'^FOR\s+(?P<index_names>[A-Z_]\w*(?:\s*,\s*[A-Z_]\w*)*)\s*IN\s*(?P<expression>.*)$')
_FORTIEL_END_FOR = _reg_expr(r'^END\s*FOR$')

_FORTIEL_MACRO = _reg_expr(r'^MACRO\s+(?P<name>[A-Z]\w*)(\s+(?P<pattern>.*))?$')
_FORTIEL_PATTERN = _reg_expr(r'^PATTERN\s+(?P<pattern>.*)$')
_FORTIEL_SECTION = _reg_expr(
    r'^SECTION\s+(?P<once>ONCE\s+)?(?P<name>[A-Z]\w*)(?:\s+(?P<pattern>.*))?$')
_FORTIEL_FINALLY = _reg_expr(r'^FINALLY$')
_FORTIEL_END_MACRO = _reg_expr(r'^END\s*MACRO$')

_MISPLACED_HEADS = [
    _make_name(head) for head in [
        'else', 'else if', 'end if', 'end do',
        'section', 'finally', 'pattern', 'end macro']]

_BUILTIN_HEADERS = {'.f90': 'tiel/syntax.fd'}


class FortielParser:
    """Fortiel syntax tree parser."""
    def __init__(self, file_path: str, lines: List[str]) -> None:
        self._file_path: str = file_path
        self._lines: List[str] = lines
        self._line: str = self._lines[0]
        self._line_index: int = 0
        self._line_number: int = 1

    def _matches_end(self) -> bool:
        return self._line_index >= len(self._lines)

    def _advance_line(self) -> None:
        self._line_index += 1
        self._line_number += 1
        self._line = '' if self._matches_end() else self._lines[self._line_index].rstrip()

    def _matches_line(self, *patterns: Pattern[str]) -> Optional[Match[str]]:
        if self._matches_end():
            message = 'unexpected end of file'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        for pattern in patterns:
            match = pattern.match(self._line)
            if match is not None:
                return match
        return None

    def _parse_line_continuation(self) -> None:
        """Parse continuation lines."""
        while self._line.endswith('&'):
            self._line: str = self._line[:-1] + ' '
            self._line_index += 1
            self._line_number += 1
            if self._matches_end():
                message = 'unexpected end of file in continuation lines'
                raise FortielSyntaxError(message, self._file_path, self._line_number)
            next_line = self._lines[self._line_index].lstrip()
            if next_line.startswith('&'):
                next_line = next_line[1:].lstrip()
            self._line += next_line.rstrip()

    def parse(self) -> FortielTree:
        """Parse the source lines."""
        tree = FortielTree(self._file_path)
        # Add builtin headers based on file extension.
        _, file_ext = path.splitext(self._file_path)
        builtins_path = _BUILTIN_HEADERS.get(file_ext.lower())
        if builtins_path is not None:
            use_builtins_node = FortielNodeUse(self._file_path, self._line_number)
            use_builtins_node.imported_file_path = builtins_path
            tree.root_nodes.append(use_builtins_node)
        # Parse file contents.
        while not self._matches_end():
            tree.root_nodes.append(self._parse_statement())
        return tree

    @staticmethod
    def _parse_head(directive: Optional[str]) -> Optional[str]:
        # Empty directives does not have a head.
        if directive is None or directive == '':
            return None
        # ELSE is merged with IF, END is merged with any following word.
        dir_head_word, dir_head_word2 = _DIR_HEAD.match(directive).group('word', 'word2')
        dir_head = dir_head_word.lower()
        if dir_head_word2 is not None:
            dir_head_word2 = dir_head_word2.lower()
            if dir_head_word == 'end' or (dir_head_word == 'else' and dir_head_word2 == 'if'):
                dir_head += dir_head_word2
        return dir_head

    def _parse_statement(self) -> FortielNode:
        """Parse a directive or a line list."""
        if self._matches_line(_FORTIEL_DIRECTIVE):
            return self._parse_directive()
        if self._matches_line(_FORTIEL_CALL):
            self._parse_line_continuation()
            return self._parse_directive_call()
        return self._parse_line_list()

    def _parse_line_list(self) -> FortielNodeLineList:
        """Parse a line list."""
        node = FortielNodeLineList(self._file_path, self._line_number)
        while True:
            node.lines.append(self._line)
            self._advance_line()
            if self._matches_end() or self._matches_line(_FORTIEL_DIRECTIVE, _FORTIEL_CALL):
                break
        return node

    def _parse_directive(self) -> FortielNode:
        """Parse a directive."""
        self._parse_line_continuation()
        directive = self._matches_line(_FORTIEL_DIRECTIVE)['directive']
        head = type(self)._parse_head(directive)
        if head is None:
            message = 'empty directive'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        if (func := {'use': self._parse_directive_use,
                     'let': self._parse_directive_let,
                     'define': self._parse_directive_define,
                     'del': self._parse_directive_del,
                     'if': self._parse_directive_if,
                     'do': self._parse_directive_do,
                     'for': self._parse_directive_for,
                     'macro': self._parse_directive_macro
                     }.get(head)) is not None:
            return func()
        # Determine the error type:
        # either the known directive is misplaced, either the directive is unknown.
        if head in map(_make_name, {'else', 'else if', 'end if', 'end do',
                                    'section', 'finally', 'pattern', 'end macro'}):
            message = f'misplaced directive <{head}>'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        message = f'unknown or mistyped directive <{head}>'
        raise FortielSyntaxError(message, self._file_path, self._line_number)

    def _matches_directive(self, *expected_heads: str) -> Optional[str]:
        match = self._matches_line(_FORTIEL_DIRECTIVE)
        if match is not None:
            # Parse continuations and rematch.
            self._parse_line_continuation()
            match = self._matches_line(_FORTIEL_DIRECTIVE)
            directive = match['directive'].lower()
            head = type(self)._parse_head(directive)
            if head in map(_make_name, expected_heads):
                return head
        return None

    def _match_directive_syntax(
            self, pattern: Pattern[str], *groups: str) -> Union[str, Tuple[str, ...]]:
        directive = self._matches_line(_FORTIEL_DIRECTIVE)['directive'].rstrip()
        if (match := pattern.match(directive)) is None:
            head = type(self)._parse_head(directive)
            message = f'invalid <{head}> directive syntax'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        self._advance_line()
        return match.group(*groups)

    def _parse_directive_use(self) -> FortielNodeUse:
        """Parse USE directive."""
        node = FortielNodeUse(self._file_path, self._line_number)
        node.imported_file_path = self._match_directive_syntax(_FORTIEL_USE, 'path')
        # Remove quotes.
        node.imported_file_path = node.imported_file_path[1:-1]
        return node

    def _parse_directive_let(self) -> FortielNodeLet:
        """Parse LET directive."""
        # Note that we are not evaluating or
        # validating define arguments and body here.
        node = FortielNodeLet(self._file_path, self._line_number)
        node.name, node.arguments, node.expression = \
            self._match_directive_syntax(_FORTIEL_LET, 'name', 'arguments', 'expression')
        if node.arguments is not None:
            # Remove parentheses and split by commas.
            node.arguments = map(str.strip, node.arguments[1:-1].split(','))
        return node

    def _parse_directive_define(self) -> FortielNodeDefine:
        """Parse DEFINE directive."""
        # Note that we are not evaluating or validating define segment here.
        node = FortielNodeDefine(self._file_path, self._line_number)
        node.name, node.segment = self._match_directive_syntax(_FORTIEL_DEFINE, 'name', 'segment')
        return node

    def _parse_directive_del(self) -> FortielNodeDel:
        """Parse DEL directive."""
        # Note that we are not evaluating or validating define name here.
        node = FortielNodeDel(self._file_path, self._line_number)
        names = self._match_directive_syntax(_FORTIEL_DEL, 'names')
        node.names = map(str.strip, names.split(','))
        return node

    def _parse_directive_if(self) -> FortielNodeIf:
        """Parse IF/ELSE IF/ELSE/END IF directive."""
        # Note that we are not evaluating or validating condition expressions here.
        node = FortielNodeIf(self._file_path, self._line_number)
        node.condition = self._match_directive_syntax(_FORTIEL_IF, 'condition')
        while not self._matches_directive('else if', 'else', 'end if'):
            node.then_nodes.append(self._parse_statement())
        if self._matches_directive('else if'):
            while not self._matches_directive('else', 'end if'):
                elif_node = FortielNodeElseIf(self._file_path, self._line_number)
                elif_node.condition = self._match_directive_syntax(_FORTIEL_ELSE_IF, 'condition')
                while not self._matches_directive('else if', 'else', 'end if'):
                    elif_node.then_nodes.append(self._parse_statement())
                node.elif_nodes.append(elif_node)
        if self._matches_directive('else'):
            self._match_directive_syntax(_FORTIEL_ELSE)
            while not self._matches_directive('end if'):
                node.else_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_IF)
        return node

    def _parse_directive_do(self) -> FortielNodeDo:
        """Parse DO/END DO directive."""
        # Note that we are not evaluating or validating loop bound expressions here.
        node = FortielNodeDo(self._file_path, self._line_number)
        node.index_name, node.ranges = \
            self._match_directive_syntax(_FORTIEL_DO, 'index_name', 'ranges')
        while not self._matches_directive('end do'):
            node.loop_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_DO)
        return node

    def _parse_directive_for(self) -> FortielNodeFor:
        """Parse FOR/END FOR directive."""
        # Note that we are not evaluating or validating loop expressions here.
        node = FortielNodeFor(self._file_path, self._line_number)
        node.index_names, node.ranges_expression = \
            self._match_directive_syntax(_FORTIEL_FOR, 'index_names', 'expression')
        node.index_names = [name.strip() for name in node.index_names.split(',')]
        while not self._matches_directive('end for'):
            node.loop_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_FOR)
        return node

    def _parse_directive_macro(self) -> FortielNodeMacro:
        """Parse MACRO/END MACRO directive."""
        node = FortielNodeMacro(self._file_path, self._line_number)
        node.name, pattern = self._match_directive_syntax(_FORTIEL_MACRO, 'name', 'pattern')
        node.name = _make_name(node.name)
        node.pattern_nodes = self._parse_directive_pattern_list(node, pattern)
        if self._matches_directive('section'):
            while not self._matches_directive('finally', 'end macro'):
                sect_node = FortielNodeSection(self._file_path, self._line_number)
                sect_node.name, sect_node.once, pattern = \
                    self._match_directive_syntax(_FORTIEL_SECTION, 'name', 'once', 'pattern')
                sect_node.name = _make_name(sect_node.name)
                sect_node.once = sect_node.once is not None
                sect_node.pattern_nodes = self._parse_directive_pattern_list(sect_node, pattern)
                node.section_nodes.append(sect_node)
        if self._matches_directive('finally'):
            self._match_directive_syntax(_FORTIEL_FINALLY)
            while not self._matches_directive('end macro'):
                node.finally_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_MACRO)
        return node

    def _parse_directive_pattern_list(
            self, node: Union[FortielNodeMacro, FortielNodeSection],
            pattern: Optional[str]) -> List[FortielNodePattern]:
        """Parse PATTERN directive list."""
        pattern_nodes: List[FortielNodePattern] = []
        if pattern is not None:
            pattern_node = FortielNodePattern(node.file_path, node.line_number)
            pattern_node.pattern = pattern
            while not self._matches_directive('pattern', 'section', 'finally', 'end macro'):
                pattern_node.match_nodes.append(self._parse_statement())
            pattern_nodes.append(pattern_node)
        elif not self._matches_directive('pattern'):
            message = 'expected <pattern> directive'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        if self._matches_directive('pattern'):
            while not self._matches_directive('section', 'finally', 'end macro'):
                pattern_node = FortielNodePattern(self._file_path, self._line_number)
                pattern_node.pattern = self._match_directive_syntax(_FORTIEL_PATTERN, 'pattern')
                while not self._matches_directive('pattern', 'section', 'finally', 'end macro'):
                    pattern_node.match_nodes.append(self._parse_statement())
                pattern_nodes.append(pattern_node)
        # Compile the patterns.
        for pattern_node in pattern_nodes:
            try:
                pattern = _reg_expr(pattern_node.pattern)
            except re.error as error:
                message = f'invalid pattern regular expression `{pattern_node.pattern}`'
                raise FortielSyntaxError(
                    message, pattern_node.file_path, pattern_node.line_number) from error
            else:
                pattern_node.pattern = pattern
        return pattern_nodes

    def _parse_directive_call(self) -> FortielNodeCallSegment:
        """Parse call directive."""
        # Note that we are not evaluating or matching call arguments and sections here.
        node = FortielNodeCallSegment(self._file_path, self._line_number)
        # Call directive uses different syntax, so it cannot be parsed with common routines.
        match = self._matches_line(_FORTIEL_CALL)
        if match is None:
            message = 'invalid call segment syntax'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        self._advance_line()
        node.spaces, node.name, node.argument = match.group('spaces', 'name', 'argument')
        node.name = _make_name(node.name)
        node.argument = node.argument.strip()
        return node


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=              Fortiel Directives Executor              =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


_FORTIEL_INLINE_EVAL = _reg_expr(r'\${(?P<expression>.+?)}\$')
_FORTIEL_INLINE_SHORT_EVAL = _reg_expr(r'[$@]\s*(?P<expression>\w+)\b')

_FORTIEL_INLINE_SHORT_LOOP = _reg_expr(
    r'(?P<comma_before>,\s*)?[\^@](?P<expression>(?::|\w+))(?P<comma_after>\s*,)?')
_FORTIEL_INLINE_LOOP = _reg_expr(
    r'(?P<comma_before>,\s*)?[\^@]{(?P<expression>.*?)}[\^@](?P<comma_after>\s*,)?')

_BUILTIN_NAMES = ['__INDEX__', '__FILE__', '__LINE__', '__DATE__', '__TIME__']

FortielPrintFunc = Callable[[str], None]


class FortielExecutor:
    """Fortiel syntax tree executor."""
    def __init__(self, options: FortielOptions):
        self._scope: Dict[str, Any] = {}
        self._macros: Dict[str, FortielNodeMacro] = {}
        self._imported_files_paths: Set[str] = set()
        self._options: FortielOptions = options

    def execute_tree(self, tree: FortielTree, print_func: FortielPrintFunc) -> None:
        """Execute the syntax tree or the syntax tree node."""
        # Print primary line marker.
        if self._options.line_marker_format == 'fpp':
            print_func(f'# 1 "{tree.file_path}" 1')
        elif self._options.line_marker_format == 'cpp':
            print_func(f'#line 1 "{tree.file_path}" 1')
        # Execute tree nodes.
        self._execute_node_list(tree.root_nodes, print_func)

    def _evaluate_expression(self, expression: str, file_path: str, line_number: int) -> Any:
        """Evaluate Python expression."""
        try:
            value = eval(expression, self._scope)
            return value
        except Exception as error:
            txt = str(error)
            txt = txt.replace("<head>", f"expression `{expression}`")
            txt = txt.replace("<string>", f"expression `{expression}`")
            message = f'Python expression evaluation error: {txt}'
            raise FortielRuntimeError(message, file_path, line_number) from error

    def _evaluate_line(self, line: str, file_path: str, line_number: int) -> str:
        """Execute in-line substitutions."""

        def _evaluate_inline_loop_expression_sub(match: Match[str]) -> str:
            # Evaluate <^:> and <^{..}^> substitutions.
            if (index := self._scope.get('__INDEX__')) is None:
                message = '<^{..}^> substitution outside of the <do> loop body'
                raise FortielRuntimeError(message, file_path, line_number)
            expression, comma_before, comma_after = \
                match.group('expression', 'comma_before', 'comma_after')
            if index == 0:
                # Empty substitution, replace with a single comma if needed.
                sub = ',' if (comma_before is not None) and (comma_after is not None) else ''
            else:
                sub = ','.join(
                    [e.replace('$$', str(i + 1)) for i, e in enumerate(index * [expression])])
                if comma_before is not None:
                    sub = comma_before + sub
                if comma_after is not None:
                    sub += comma_after
            # Recursively evaluate inner substitutions.
            return self._evaluate_line(sub, file_path, line_number)

        line = _FORTIEL_INLINE_LOOP.sub(_evaluate_inline_loop_expression_sub, line)
        line = _FORTIEL_INLINE_SHORT_LOOP.sub(_evaluate_inline_loop_expression_sub, line)

        def _evaluate_inline_eval_expression_sub(match: Match[str]) -> str:
            # Evaluate <$..> and <${..}$> substitutions.
            expression = match['expression']
            value = self._evaluate_expression(expression, file_path, line_number)
            # Put negative number into parentheses.
            if isinstance(value, (int, float)) and (value < 0):
                sub = f'({value})'
            else:
                sub = str(value)
            # Recursively evaluate inner substitutions.
            return self._evaluate_line(sub, file_path, line_number)

        line = _FORTIEL_INLINE_EVAL.sub(_evaluate_inline_eval_expression_sub, line)
        if (striped := line.lstrip().lower()).startswith('!$omp') or striped.startswith('!$acc'):
            # Special case for OpenMP/OpenACC directives.
            cut = len(line) - len(striped) + len('!$')
            line = \
                line[:cut] + \
                _FORTIEL_INLINE_SHORT_EVAL.sub(_evaluate_inline_eval_expression_sub, line[cut:])
        else:
            line = _FORTIEL_INLINE_SHORT_EVAL.sub(_evaluate_inline_eval_expression_sub, line)

        # Output the processed line.
        return line

    def _execute_node(self, node: FortielNode, print_func: FortielPrintFunc) -> None:
        """Execute a node."""
        for nodeType, func in {
                FortielNodeUse: self._execute_node_use,
                FortielNodeLet: self._execute_node_let,
                FortielNodeDefine: self._execute_node_define,
                FortielNodeDel: self._execute_node_del,
                FortielNodeIf: self._execute_node_if,
                FortielNodeDo: self._execute_node_do,
                FortielNodeFor: self._execute_node_for,
                FortielNodeMacro: self._execute_node_macro,
                FortielNodeCall: self._execute_node_call,
                FortielNodeLineList: self._execute_node_line_list}.items():
            if isinstance(node, nodeType):
                func = cast(Callable[[FortielNode, FortielPrintFunc], None], func)
                return func(node, print_func)
        node_type = type(node).__name__
        raise RuntimeError(f'internal error: no evaluator for directive type {node_type}')

    def _execute_node_list(self, nodes: List[FortielNode], print_func: FortielPrintFunc) -> None:
        """Execute the node list."""
        index = 0
        while index < len(nodes):
            if isinstance(nodes[index], FortielNodeCallSegment):
                self._resolve_call_segment(index, nodes)
            self._execute_node(nodes[index], print_func)
            index += 1

    def _execute_node_line_list(
            self, node: FortielNodeLineList, print_func: FortielPrintFunc) -> None:
        """Execute line block."""
        # Print line marker.
        if self._options.line_marker_format == 'fpp':
            print_func(f'# {node.line_number} "{node.file_path}"')
        elif self._options.line_marker_format == 'cpp':
            print_func(f'#line {node.line_number} "{node.file_path}"')
        # Print lines.
        for line_number, line in enumerate(node.lines, start=node.line_number):
            print_func(self._evaluate_line(line, node.file_path, line_number))

    def _execute_node_use(self, node: FortielNodeUse, _: FortielPrintFunc) -> None:
        """Execute USE node."""
        # Resolve file path.
        node_dir_path = path.dirname(node.file_path)
        imported_file_path = _find_file(
            node.imported_file_path, self._options.include_paths + [node_dir_path])
        if imported_file_path is None:
            message = f'`{node.imported_file_path}` was not found in the include paths'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        # Ensure that file is used only once.
        if imported_file_path not in self._imported_files_paths:
            self._imported_files_paths.add(imported_file_path)
            try:
                with open(imported_file_path, mode='r') as imported_file:
                    imported_file_lines = imported_file.read().splitlines()
            except IsADirectoryError as error:
                message = f'`{node.imported_file_path}` is a directory'
                raise FortielRuntimeError(message, node.file_path, node.line_number) from error
            except IOError as error:
                message = f'unable to read file `{node.imported_file_path}`'
                raise FortielRuntimeError(message, node.file_path, node.line_number) from error
            # Parse and execute the dependency.
            # ( Use a dummy print_func in order to skip code lines. )
            imported_tree = FortielParser(node.imported_file_path, imported_file_lines).parse()
            self.execute_tree(imported_tree, (lambda _: None))

    def _execute_node_let(self, node: FortielNodeLet, _: FortielPrintFunc) -> None:
        """Execute LET node."""
        # Check if the variable is not already defined, and is not a build-in name.
        if node.name in self._scope:
            message = f'name `{node.name}` is already defined'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        if node.name in _BUILTIN_NAMES:
            message = f'builtin name <{node.name}> can not be redefined'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        if node.arguments is None:
            # Evaluate variable.
            self._scope[node.name] = \
                self._evaluate_expression(node.expression, node.file_path, node.line_number)
        else:
            # Evaluate variable as lambda function.
            if not isinstance(node.arguments, list):
                # TODO: fix for '*' prefix.
                node.arguments = [name.strip() for name in node.arguments.split(',')]
                if (arg := _find_duplicate(node.arguments)) is not None:
                    message = f'duplicate argument `{arg}` of the functional <let>'
                    raise FortielRuntimeError(message, node.file_path, node.line_number)
            expression = f'lambda {node.arguments}: {node.expression}'
            function = self._evaluate_expression(expression, node.file_path, node.line_number)
            self._scope[node.name] = function

    def _execute_node_define(self, node: FortielNodeDefine, _: FortielPrintFunc) -> None:
        """Execute DEFINE node."""
        # Check if the variable is not a build-in name.
        if node.name in _BUILTIN_NAMES:
            message = f'builtin name <{node.name}> can not be redefined'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        # Evaluate segment.
        value = self._evaluate_line(node.segment, node.file_path, node.line_number)
        self._scope[node.name] = value

    def _execute_node_del(self, node: FortielNodeDel, _: FortielPrintFunc) -> None:
        """Execute DEL node."""
        for name in node.names:
            if name not in self._scope:
                message = f'name `{name}` was not previously defined'
                raise FortielRuntimeError(message, node.file_path, node.line_number)
            if name in _BUILTIN_NAMES:
                message = f'builtin name <{name}> can not be undefined'
                raise FortielRuntimeError(message, node.file_path, node.line_number)
            del self._scope[name]

    def _execute_node_if(self, node: FortielNodeIf, print_func: FortielPrintFunc) -> None:
        """Execute IF/ELSE IF/ELSE/END IF node."""
        # Evaluate condition and execute THEN branch.
        if self._evaluate_expression(node.condition, node.file_path, node.line_number):
            self._execute_node_list(node.then_nodes, print_func)
        else:
            # Evaluate condition and execute ELSE IF branches.
            for elif_node in node.elif_nodes:
                if self._evaluate_expression(
                        elif_node.condition, elif_node.file_path, elif_node.line_number):
                    self._execute_node_list(elif_node.then_nodes, print_func)
                    break
            else:
                # Execute ELSE branch.
                self._execute_node_list(node.else_nodes, print_func)

    def _execute_node_do(self, node: FortielNodeDo, print_func: FortielPrintFunc) -> None:
        """Execute DO/END DO node."""
        # Evaluate loop ranges.
        ranges = self._evaluate_expression(
            node.ranges, node.file_path, node.line_number)
        if not (isinstance(ranges, tuple) and (2 <= len(ranges) <= 3) and
                list(map(type, ranges)) == len(ranges) * [int]):
            message = 'tuple of two or three integers inside the <do> ' + \
                      f'directive ranges is expected, got `{node.ranges}`'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        start, stop = ranges[0:2]
        step = ranges[2] if len(ranges) == 3 else 1
        ranges = range(start, stop + step, step)
        if len(ranges) > 0:
            # Save previous index value
            # in case we are inside the nested loop.
            prev_index = self._scope.get('__INDEX__')
            for index in ranges:
                # Execute loop body.
                self._scope[node.index_name] = index
                self._scope['__INDEX__'] = index
                self._execute_node_list(node.loop_nodes, print_func)
            del self._scope[node.index_name]
            # Restore previous index value.
            self._scope['__INDEX__'] = prev_index

    def _execute_node_for(self, node: FortielNodeFor, print_func: FortielPrintFunc) -> None:
        """Execute FOR/END FOR node."""
        # Evaluate loop.
        iterable = self._evaluate_expression(
            node.ranges_expression, node.file_path, node.line_number)
        if isinstance(iterable, dict):
            for key, value in iterable.items():
                if len(node.index_names) == 1:
                    self._scope[node.index_names[0]] = value
                else:
                    self._scope[node.index_names[0]] = key
                    self._scope[node.index_names[1]] = value
                self._execute_node_list(node.loop_nodes, print_func)
        else:
            for index_values in iterable:
                if len(node.index_names) == 1:
                    self._scope[node.index_names[0]] = index_values
                else:
                    for index_name, index_value in zip(node.index_names, index_values):
                        self._scope[index_name] = index_value
                self._execute_node_list(node.loop_nodes, print_func)
        for index_name in node.index_names:
            del self._scope[index_name]

    def _execute_node_macro(self, node: FortielNodeMacro, _: FortielPrintFunc) -> None:
        """Execute MACRO/END MACRO node."""
        if node.name in self._macros:
            message = f'macro `{node.name}` is already defined'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        if len(node.section_nodes) > 0:
            sections = node.section_names()
            if node.name in sections:
                message = f'section name cannot be the same with macro `{node.name}` name'
                raise FortielRuntimeError(message, node.file_path, node.line_number)
            if (dup := _find_duplicate(sections)) is not None:
                message = f'duplicate section `{dup}` of the macro construct `{node.name}`'
                raise FortielRuntimeError(message, node.file_path, node.line_number)
        # Add macro to the scope.
        self._macros[node.name] = node

    def _resolve_call_segment(self, index: int, nodes: List[FortielNode]) -> None:
        """Resolve call segments."""
        node = cast(FortielNodeCallSegment, nodes[index])
        macro_node = self._macros.get(node.name)
        if macro_node is None:
            message = f'macro `{node.name}` was not previously defined'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        # Convert current node to call node and replace it in the node list.
        node = nodes[index] = FortielNodeCall(node)
        if macro_node.construct():
            # Pop and process nodes until the end of macro construct call is reached.
            next_index = index + 1
            end_name = 'end' + node.name
            while len(nodes) > next_index:
                next_node = nodes[next_index]
                if isinstance(next_node, FortielNodeCallSegment):
                    if next_node.name == end_name:
                        nodes.pop(next_index)
                        break
                    if next_node.name in macro_node.section_names():
                        call_section_node = FortielNodeCallSection(next_node)
                        node.call_section_nodes.append(call_section_node)
                        nodes.pop(next_index)
                        continue
                    # Resolve the scoped call.
                    self._resolve_call_segment(next_index, nodes)
                # Append the current node to the most recent section of the call node.
                next_node = nodes.pop(next_index)
                if len(node.call_section_nodes) == 0:
                    node.captured_nodes.append(next_node)
                else:
                    section_node = node.call_section_nodes[-1]
                    section_node.captured_nodes.append(next_node)
            else:
                message = f'expected `@{end_name}` call segment'
                raise FortielRuntimeError(message, node.file_path, node.line_number)

    def _execute_node_call(self, node: FortielNodeCall, print_func: FortielPrintFunc) -> None:
        """Execute CALL node."""

        # Use a special print function
        # in order to keep indentations from the original source.
        # ( Note that we have to keep line markers not indented. )
        def _spaced_print_func(line: str):
            print_func(line if line.startswith('#') else node.spaces + line)

        macro_node = self._macros[node.name]
        self._execute_node_pattern_list(node, macro_node, _spaced_print_func)
        # Match and evaluate macro sections.
        if macro_node.construct():
            self._execute_node_list(node.captured_nodes, print_func)
            section_iterator = iter(macro_node.section_nodes)
            section_node = next(section_iterator, None)
            for call_section_node in node.call_section_nodes:
                # Find a section node match.
                while section_node is not None and \
                        section_node.name != call_section_node.name:
                    section_node = next(section_iterator, None)
                if section_node is None:
                    message = f'unexpected call section `{call_section_node.name}`'
                    raise FortielRuntimeError(
                        message, call_section_node.file_path, call_section_node.line_number)
                # Execute the section.
                self._execute_node_pattern_list(
                    call_section_node, section_node, _spaced_print_func)
                self._execute_node_list(call_section_node.captured_nodes, print_func)
                # Advance a section for sections with 'once' attribute.
                if section_node.once:
                    section_node = next(section_iterator, None)
            # Execute finally section.
            self._execute_node_list(macro_node.finally_nodes, _spaced_print_func)

    def _execute_node_pattern_list(
            self, node: Union[FortielNodeCall, FortielNodeCallSection],
            macro_node: Union[FortielNodeMacro, FortielNodeSection],
            print_func: FortielPrintFunc) -> None:
        # Find a match in macro or section patterns and
        # execute macro primary section or current section.
        for pattern_node in macro_node.pattern_nodes:
            match = pattern_node.pattern.match(node.argument)
            if match is not None:
                self._scope = {**self._scope, **match.groupdict()}
                self._execute_node_list(pattern_node.match_nodes, print_func)
                break
        else:
            message = f'macro `{macro_node.name}` call does not match any pattern'
            raise FortielRuntimeError(message, node.file_path, node.line_number)


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=              Fortiel API and Entry Point              =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


def fortiel_preprocess(
        file_path: str, output_file_path: str, options: FortielOptions = FortielOptions()) -> None:
    """Preprocess the source file."""
    with open(file_path, 'r') as file:
        lines = file.read().splitlines()
    tree = FortielParser(file_path, lines).parse()
    with open(output_file_path, 'w') as output_file:

        def _print_func(line):
            print(line, file=output_file)

        FortielExecutor(options).execute_tree(tree, _print_func)


def main() -> None:
    """Fortiel entry point."""
    # Make CLI description and parse it.
    arg_parser = argparse.ArgumentParser()
    # Preprocessor definitions.
    arg_parser.add_argument(
        '-D', '--define', metavar='name[=value]',
        action='append', dest='defines', default=[],
        help='define a named variable')
    # Preprocessor include directories.
    arg_parser.add_argument(
        '-I', '--include', metavar='includeDir',
        action='append', dest='include_dirs', default=[],
        help='add an include directory path')
    # Line marker format.
    arg_parser.add_argument(
        '-M', '--line_markers',
        choices=['fpp', 'cpp', 'none'], default=FortielOptions().line_marker_format,
        help='line markers format')
    # Input and output file paths.
    arg_parser.add_argument(
        'file_path',
        help='input file path')
    arg_parser.add_argument(
        'output_file_path',
        help='output file path')
    args = arg_parser.parse_args()
    # Get input and output file paths.
    file_path = args.file_path
    output_file_path = args.output_file_path
    # Get other options.
    options = FortielOptions()
    options.defines += args.defines
    options.include_paths += args.include_dirs
    options.line_marker_format = args.line_markers
    # Execute the compiler.
    fortiel_preprocess(file_path, output_file_path, options)


if __name__ == '__main__':
    main()
