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
from abc import ABC
from dataclasses import dataclass, field
from keyword import iskeyword as is_reserved

from typing import (
    cast, final,
    Iterable, List, Set, Dict, Tuple, Any, Union,
    Final, Optional, Callable, Literal, Pattern, Match)


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=                Fortiel Helper Routines                =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


def _make_name(name: str) -> str:
    """Compile a single-word lower case identifier."""
    return re.sub(r'\s+', '', name).lower()


def _compile_re(pattern: str) -> Pattern[str]:
    """Compile regular expression."""
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.VERBOSE)


def _find_duplicate(strings: Iterable[str]) -> Optional[str]:
    """Find first duplicate in the list."""
    strings_set: Set[str] = set()
    for string in strings:
        if string in strings_set:
            return string
        strings_set.add(string)
    return None


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
    # TODO: refactor as data class.
    def __init__(self) -> None:
        self.defines: List[str] = []
        self.include_paths: List[str] = []
        self.line_marker_format: Literal['fpp', 'cpp', 'none'] = 'fpp'


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=         Fortiel Scanner and Directives Parser         =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


@dataclass
class FortielNode(ABC):
    """Fortiel syntax tree node."""
    file_path: str
    line_number: int


@final
@dataclass
class FortielTree:
    """Fortiel syntax tree."""
    file_path: str
    root_nodes: List[FortielNode] = field(default_factory=list)


@final
@dataclass
class FortielLineListNode(FortielNode):
    """The list of code lines syntax tree node."""
    lines: List[str] = field(default_factory=list)


@final
@dataclass
class FortielUseNode(FortielNode):
    """The USE directive syntax tree node."""
    imported_file_path: str


@final
@dataclass
class FortielLetNode(FortielNode):
    """The LET directive syntax tree node."""
    name: str
    arguments: Union[str, List[str], None]
    value_expression: str


@final
@dataclass
class FortielDelNode(FortielNode):
    """The DEL directive syntax tree node."""
    names: Union[str, List[str]]


@final
@dataclass
class FortielElifNode(FortielNode):
    """The ELSE IF directive syntax tree node."""
    condition_expression: str
    then_nodes: List[FortielNode] = field(default_factory=list)


@final
@dataclass
class FortielIfNode(FortielNode):
    """The IF/ELSE IF/ELSE/END IF directive syntax tree node."""
    condition_expression: str
    then_nodes: List[FortielNode] = field(default_factory=list)
    elif_nodes: List[FortielElifNode] = field(default_factory=list)
    else_nodes: List[FortielNode] = field(default_factory=list)


@final
@dataclass
class FortielDoNode(FortielNode):
    """The DO/END DO directive syntax tree node."""
    index_name: str
    ranges_expression: str
    loop_nodes: List[FortielNode] = field(default_factory=list)


@final
@dataclass
class FortielForNode(FortielNode):
    """The FOR/END FOR directive syntax tree node."""
    index_names: Union[str, List[str], None]
    iterable_expression: str
    loop_nodes: List[FortielNode] = field(default_factory=list)


@final
@dataclass
class FortielCallSegmentNode(FortielNode):
    """The call segment syntax tree node."""
    spaces_before: str
    name: str
    argument: str


@final
@dataclass
class FortielPatternNode(FortielNode):
    """The PATTERN directive syntax tree node."""
    pattern: Union[str, Pattern[str]]
    match_nodes: List[FortielNode] = field(default_factory=list)


@final
@dataclass
class FortielSectionNode(FortielNode):
    """The SECTION directive syntax tree node."""
    name: str
    once: bool
    pattern_nodes: List[FortielPatternNode] = field(default_factory=list)


@final
@dataclass
class FortielMacroNode(FortielNode):
    """The MACRO/END MACRO directive syntax tree node."""
    name: str
    pattern_nodes: List[FortielPatternNode] = field(default_factory=list)
    section_nodes: List[FortielSectionNode] = field(default_factory=list)
    finally_nodes: List[FortielNode] = field(default_factory=list)

    @property
    def is_construct(self) -> bool:
        """Is current macro a construct?"""
        return len(self.section_nodes) > 0 or len(self.finally_nodes) > 0

    @property
    def section_names(self) -> List[str]:
        """List of the section names."""
        return [node.name for node in self.section_nodes]


@final
class FortielCallNode(FortielNode):
    """The call directive syntax tree node."""
    # TODO: refactor as data class.
    def __init__(self, node: FortielCallSegmentNode) -> None:
        super().__init__(node.file_path, node.line_number)
        self.spaces_before: str = node.spaces_before
        self.name: str = node.name
        self.argument: str = node.argument
        self.captured_nodes: List[FortielNode] = []
        self.call_section_nodes: List[FortielCallSectionNode] = []


@final
class FortielCallSectionNode(FortielNode):
    """The call directive section syntax tree node."""
    # TODO: refactor as data class.
    def __init__(self, node: FortielCallSegmentNode) -> None:
        super().__init__(node.file_path, node.line_number)
        self.name: str = node.name
        self.argument: str = node.argument
        self.captured_nodes: List[FortielNode] = []


_FORTIEL_DIRECTIVE: Final = _compile_re(r'^\s*\#[@$]\s*(?P<directive>.*)?$')

_FORTIEL_USE: Final = _compile_re(
    r'^USE\s+(?P<path>(?:\"[^\"]+\") | (?:\'[^\']+\') | (?:\<[^\>]+\>))$')

_FORTIEL_LET: Final = _compile_re(r'''
    ^LET\s+(?P<name>[A-Z_]\w*)\s*
    (?: \(\s* (?P<arguments> 
                (?:\*\s*){0,2}[A-Z_]\w* 
                (?:\s*,\s*(?:\*\s*){0,2}[A-Z_]\w* )* ) \s*\) )?
    \s*=\s*(?P<value_expression>.*)$
    ''')
_FORTIEL_DEFINE: Final = _compile_re(r'^DEFINE\s+(?P<name>[A-Z_]\w*)(?P<segment>.*)$')
_FORTIEL_DEL: Final = _compile_re(r'^DEL\s+(?P<names>[A-Z_]\w*(?:\s*,\s*[A-Z_]\w*)*)$')

_FORTIEL_IF: Final = _compile_re(r'^IF\s*(?P<condition_expression>.+)$')
_FORTIEL_ELIF: Final = _compile_re(r'^ELSE\s*IF\s*(?P<condition_expression>.+)$')
_FORTIEL_ELSE: Final = _compile_re(r'^ELSE$')
_FORTIEL_END_IF: Final = _compile_re(r'^END\s*IF$')

_FORTIEL_IFDEF: Final = _compile_re(r'^IFDEF\s+(?P<name>[A-Z_]\w*)$')
_FORTIEL_IFNDEF: Final = _compile_re(r'^IFNDEF\s+(?P<name>[A-Z_]\w*)$')

_FORTIEL_DO: Final = _compile_re(
    r'^DO\s+(?P<index_name>[A-Z_]\w*)\s*=\s*(?P<ranges_expression>.*)$')
_FORTIEL_END_DO: Final = _compile_re(r'^END\s*DO$')

_FORTIEL_FOR: Final = _compile_re(
    r'^FOR\s+(?P<index_names>[A-Z_]\w*(?:\s*,\s*[A-Z_]\w*)*)\s*IN\s*(?P<iterable_expression>.*)$')
_FORTIEL_END_FOR: Final = _compile_re(r'^END\s*FOR$')

_FORTIEL_CALL: Final = _compile_re(
    r'^(?P<spaces>\s*)\@(?P<name>(?:END\s*|ELSE\s*)?[A-Z]\w*)\b(?P<argument>[^!]*)(\s*!.*)?$')

_FORTIEL_MACRO: Final = _compile_re(r'^MACRO\s+(?P<name>[A-Z]\w*)(\s+(?P<pattern>.*))?$')
_FORTIEL_PATTERN: Final = _compile_re(r'^PATTERN\s+(?P<pattern>.*)$')
_FORTIEL_SECTION: Final = _compile_re(
    r'^SECTION\s+(?P<once>ONCE\s+)?(?P<name>[A-Z]\w*)(?:\s+(?P<pattern>.*))?$')
_FORTIEL_FINALLY: Final = _compile_re(r'^FINALLY$')
_FORTIEL_END_MACRO: Final = _compile_re(r'^END\s*MACRO$')

_BUILTIN_HEADERS = {'.f90': 'tiel/syntax.fd'}


class FortielParser:
    """Fortiel syntax tree parser."""
    def __init__(self, file_path: str, lines: List[str]) -> None:
        self._file_path: str = file_path
        self._lines: List[str] = lines
        self._line: str = self._lines[0]
        self._multiline: str = self._line
        self._line_index: int = 0
        self._line_number: int = 1

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def _matches_end(self) -> bool:
        return self._line_index >= len(self._lines)

    def _advance_line(self) -> None:
        """Advance to the next line, parsing the line continuations."""
        self._line_index += 1
        self._line_number += 1
        if self._matches_end():
            self._line = self._multiline = ''
        else:
            self._line = self._multiline = self._lines[self._line_index].rstrip()
            # Parse line continuations.
            while self._line.endswith('&'):
                self._line_index += 1
                self._line_number += 1
                if self._matches_end():
                    message = 'unexpected end of file in continuation lines'
                    raise FortielSyntaxError(message, self._file_path, self._line_number)
                # Update merged line.
                next_line = self._lines[self._line_index].rstrip()
                self._multiline += '\n' + next_line
                # Update line.
                next_line = next_line.lstrip()
                if next_line.startswith('&'):
                    next_line = next_line.removeprefix('&').lstrip()
                self._line = self._line.removesuffix('&').rstrip() + ' ' + next_line

    def _matches_line(self, *patterns: Pattern[str]) -> Optional[Match[str]]:
        if self._matches_end():
            message = 'unexpected end of file'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        for pattern in patterns:
            match = pattern.match(self._line)
            if match is not None:
                return match
        return None

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def parse(self) -> FortielTree:
        """Parse the source lines."""
        tree = FortielTree(self._file_path)
        # Add builtin headers based on file extension.
        _, file_ext = path.splitext(self._file_path)
        builtins_path = _BUILTIN_HEADERS.get(file_ext.lower())
        if builtins_path is not None:
            use_builtins_node = FortielUseNode(self._file_path, 0, builtins_path)
            tree.root_nodes.append(use_builtins_node)
        # Parse file contents.
        while not self._matches_end():
            tree.root_nodes.append(self._parse_statement())
        return tree

    def _parse_statement(self) -> FortielNode:
        """Parse a directive or a line list."""
        if self._matches_line(_FORTIEL_DIRECTIVE):
            return self._parse_directive()
        if self._matches_line(_FORTIEL_CALL):
            return self._parse_call_segment()
        return self._parse_line_list()

    def _parse_line_list(self) -> FortielLineListNode:
        """Parse a line list."""
        node = FortielLineListNode(self._file_path, self._line_number)
        while True:
            node.lines.append(self._multiline)
            self._advance_line()
            if self._matches_end() or self._matches_line(_FORTIEL_DIRECTIVE, _FORTIEL_CALL):
                break
        return node

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def _parse_directive(self) -> FortielNode:
        """Parse a directive."""
        # Parse directive head and proceed to the specific parse function.
        directive = self._matches_line(_FORTIEL_DIRECTIVE)['directive']
        head = type(self)._parse_head(directive)
        if head is None:
            message = 'empty directive'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        if (func := {'use': self._parse_use_directive,
                     'let': self._parse_let_directive,
                     'define': self._parse_define_directive,
                     'del': self._parse_del_directive,
                     'if': self._parse_if_directive,
                     'ifdef': self._parse_ifdef_directive,
                     'ifndef': self._parse_ifndef_directive,
                     'do': self._parse_do_directive,
                     'for': self._parse_for_directive,
                     'macro': self._parse_macro_directive}.get(head)) is not None:
            return func()
        # Determine the error type:
        # either the known directive is misplaced, either the directive is unknown.
        if head in map(_make_name, {'else', 'else if', 'end if', 'end do',
                                    'section', 'finally', 'pattern', 'end macro'}):
            message = f'misplaced directive <{head}>'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        message = f'unknown or mistyped directive <{head}>'
        raise FortielSyntaxError(message, self._file_path, self._line_number)

    @staticmethod
    def _parse_head(directive: Optional[str]) -> Optional[str]:
        # Empty directives does not have a head.
        if directive is None or directive == '':
            return None
        # ELSE is merged with IF, END is merged with any following word.
        head_words = directive.split(' ', 2)
        head = head_words[0].lower()
        if len(head_words) > 1:
            second_word = head_words[1].lower()
            if head == 'end' or (head == 'else' and second_word == 'if'):
                head += second_word
        return head

    def _matches_directive(self, *expected_heads: str) -> Optional[str]:
        match = self._matches_line(_FORTIEL_DIRECTIVE)
        if match is not None:
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

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def _parse_use_directive(self) -> FortielUseNode:
        """Parse USE directive."""
        node = FortielUseNode(
            self._file_path, self._line_number,
            self._match_directive_syntax(_FORTIEL_USE, 'path'))
        # Remove quotes.
        node.imported_file_path = node.imported_file_path[1:-1]
        return node

    def _parse_let_directive(self) -> FortielLetNode:
        """Parse LET directive."""
        # Note that we are not evaluating or
        # validating define arguments and body here.
        node = FortielLetNode(
            self._file_path, self._line_number,
            *self._match_directive_syntax(_FORTIEL_LET, 'name', 'arguments', 'value_expression'))
        if is_reserved(node.name):
            message = f'name `{node.name}` is a reserved word'
            raise FortielSyntaxError(message, node.file_path, node.line_number)
        # Split and verify arguments.
        if node.arguments is not None:
            node.arguments = list(map(
                (lambda arg: re.sub(r'\s', '', arg)), node.arguments.split(',')))
            naked_arguments = map((lambda arg: arg.replace('*', '')), node.arguments)
            if (dup := _find_duplicate(naked_arguments)) is not None:
                message = f'duplicate argument `{dup}` of the functional <let>'
                raise FortielSyntaxError(message, node.file_path, node.line_number)
            if len(bad_arguments := list(filter(is_reserved, naked_arguments))) != 0:
                message = f'<let> arguments `{"`, `".join(bad_arguments)}` are reserved words'
                raise FortielSyntaxError(message, node.file_path, node.line_number)
        return node

    def _parse_define_directive(self) -> FortielLetNode:
        """Parse DEFINE directive."""
        # Note that we are not evaluating or validating define segment here.
        name, segment = \
            self._match_directive_syntax(_FORTIEL_DEFINE, 'name', 'segment')
        node = FortielLetNode(
            self._file_path, self._line_number,
            name, arguments=None, value_expression=f"'{segment}'")
        if is_reserved(node.name):
            message = f'name `{node.name}` is a reserved word'
            raise FortielSyntaxError(message, node.file_path, node.line_number)
        return node

    def _parse_del_directive(self) -> FortielDelNode:
        """Parse DEL directive."""
        # Note that we are not evaluating or validating define name here.
        node = FortielDelNode(
            self._file_path, self._line_number,
            self._match_directive_syntax(_FORTIEL_DEL, 'names'))
        # Split names.
        node.names = list(map(str.strip, node.names.split(',')))
        return node

    def _parse_if_directive(self) -> FortielIfNode:
        """Parse IF/ELSE IF/ELSE/END IF directive."""
        # Note that we are not evaluating or validating condition expressions here.
        node = FortielIfNode(
            self._file_path, self._line_number,
            self._match_directive_syntax(_FORTIEL_IF, 'condition_expression'))
        while not self._matches_directive('else if', 'else', 'end if'):
            node.then_nodes.append(self._parse_statement())
        if self._matches_directive('else if'):
            while not self._matches_directive('else', 'end if'):
                elif_node = FortielElifNode(
                    self._file_path, self._line_number,
                    self._match_directive_syntax(_FORTIEL_ELIF, 'condition_expression'))
                while not self._matches_directive('else if', 'else', 'end if'):
                    elif_node.then_nodes.append(self._parse_statement())
                node.elif_nodes.append(elif_node)
        if self._matches_directive('else'):
            self._match_directive_syntax(_FORTIEL_ELSE)
            while not self._matches_directive('end if'):
                node.else_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_IF)
        return node

    def _parse_ifdef_directive(self) -> FortielIfNode:
        """Parse IFDEF/ELSE/END IF directive."""
        node = FortielIfNode(
            self._file_path, self._line_number,
            f'defined("{self._match_directive_syntax(_FORTIEL_IFDEF, "name")}")')
        while not self._matches_directive('else', 'end if'):
            node.then_nodes.append(self._parse_statement())
        if self._matches_directive('else'):
            self._match_directive_syntax(_FORTIEL_ELSE)
            while not self._matches_directive('end if'):
                node.else_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_IF)
        return node

    def _parse_ifndef_directive(self) -> FortielIfNode:
        """Parse IFNDEF/ELSE/END IF directive."""
        node = FortielIfNode(
            self._file_path, self._line_number,
            f'not defined("{self._match_directive_syntax(_FORTIEL_IFNDEF, "name")}")')
        while not self._matches_directive('else', 'end if'):
            node.then_nodes.append(self._parse_statement())
        if self._matches_directive('else'):
            self._match_directive_syntax(_FORTIEL_ELSE)
            while not self._matches_directive('end if'):
                node.else_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_IF)
        return node

    def _parse_do_directive(self) -> FortielDoNode:
        """Parse DO/END DO directive."""
        # Note that we are not evaluating or validating loop bound expression here.
        node = FortielDoNode(
            self._file_path, self._line_number,
            *self._match_directive_syntax(_FORTIEL_DO, 'index_name', 'ranges_expression'))
        if is_reserved(node.index_name):
            message = f'<do> loop index name `{node.index_name}` is a reserved word'
            raise FortielSyntaxError(message, node.file_path, node.line_number)
        while not self._matches_directive('end do'):
            node.loop_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_DO)
        return node

    def _parse_for_directive(self) -> FortielForNode:
        """Parse FOR/END FOR directive."""
        # Note that we are not evaluating or validating loop expressions here.
        node = FortielForNode(
            self._file_path, self._line_number,
            *self._match_directive_syntax(_FORTIEL_FOR, 'index_names', 'iterable_expression'))
        node.index_names = list(map(str.strip, node.index_names.split(',')))
        if len(bad_names := list(filter(is_reserved, node.index_names))) != 0:
            message = f'<for> loop index names `{"`, `".join(bad_names)}` are reserved words'
            raise FortielSyntaxError(message, node.file_path, node.line_number)
        while not self._matches_directive('end for'):
            node.loop_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_FOR)
        return node

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def _parse_call_segment(self) -> FortielCallSegmentNode:
        """Parse call segment."""
        # Call directive uses different syntax, so it cannot be parsed with common routines.
        if (match := self._matches_line(_FORTIEL_CALL)) is None:
            message = 'invalid call segment syntax'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        # Note that we are not evaluating or matching call arguments and sections here.
        node = FortielCallSegmentNode(
            self._file_path, self._line_number, *match.group('spaces', 'name', 'argument'))
        node.name = _make_name(node.name)
        node.argument = node.argument.strip()
        self._advance_line()
        return node

    def _parse_macro_directive(self) -> FortielMacroNode:
        """Parse MACRO/END MACRO directive."""
        node = FortielMacroNode(
            self._file_path, self._line_number,
            (match := self._match_directive_syntax(_FORTIEL_MACRO, 'name', 'pattern'))[0])
        node.name = _make_name(node.name)
        node.pattern_nodes = self._parse_pattern_directives_list(node, pattern=match[1])
        if self._matches_directive('section'):
            while not self._matches_directive('finally', 'end macro'):
                section_node = FortielSectionNode(
                    self._file_path, self._line_number,
                    *(match := self._match_directive_syntax(
                        _FORTIEL_SECTION, 'name', 'once', 'pattern'))[0:2])
                section_node.name = _make_name(section_node.name)
                section_node.once = section_node.once is not None
                section_node.pattern_nodes = \
                    self._parse_pattern_directives_list(section_node, pattern=match[2])
                node.section_nodes.append(section_node)
        if self._matches_directive('finally'):
            self._match_directive_syntax(_FORTIEL_FINALLY)
            while not self._matches_directive('end macro'):
                node.finally_nodes.append(self._parse_statement())
        self._match_directive_syntax(_FORTIEL_END_MACRO)
        return node

    def _parse_pattern_directives_list(
            self, node: Union[FortielMacroNode, FortielSectionNode],
            pattern: Optional[str]) -> List[FortielPatternNode]:
        """Parse PATTERN directive list."""
        pattern_nodes: List[FortielPatternNode] = []
        if pattern is not None:
            pattern_node = FortielPatternNode(node.file_path, node.line_number, pattern)
            while not self._matches_directive('pattern', 'section', 'finally', 'end macro'):
                pattern_node.match_nodes.append(self._parse_statement())
            pattern_nodes.append(pattern_node)
        elif not self._matches_directive('pattern'):
            message = 'expected <pattern> directive'
            raise FortielSyntaxError(message, self._file_path, self._line_number)
        if self._matches_directive('pattern'):
            while not self._matches_directive('section', 'finally', 'end macro'):
                pattern_node = FortielPatternNode(
                    self._file_path, self._line_number,
                    self._match_directive_syntax(_FORTIEL_PATTERN, 'pattern'))
                while not self._matches_directive('pattern', 'section', 'finally', 'end macro'):
                    pattern_node.match_nodes.append(self._parse_statement())
                pattern_nodes.append(pattern_node)
        # Compile the patterns.
        for pattern_node in pattern_nodes:
            try:
                pattern_node.pattern = _compile_re(pattern_node.pattern)
            except re.error as error:
                message = f'invalid pattern regular expression `{pattern_node.pattern}`'
                raise FortielSyntaxError(
                    message, pattern_node.file_path, pattern_node.line_number) from error
        return pattern_nodes


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=              Fortiel Directives Executor              =-=-=-=-= #
# =-=-=-=-=-=-=-=                                           =-=-=-=-=-=-=-= #
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #


FortielPrintFunc = Callable[[str], None]

_FORTIEL_INLINE_EVAL: Final = _compile_re(r'\${(?P<expression>.+?)}\$')
_FORTIEL_INLINE_SHORT_EVAL: Final = _compile_re(r'[$@]\s*(?P<expression>\w+)\b')

_FORTIEL_INLINE_SHORT_LOOP: Final = _compile_re(r'''
    (?P<comma_before>,\s*)?
        [\^@](?P<expression>:|\w+) (?P<comma_after>\s*,)?''')
_FORTIEL_INLINE_LOOP: Final = _compile_re(r'''
    (?P<comma_before>,\s*)?
       [\^@]{ (?P<expression>.*?) ([\^@]\|[\^@] (?P<ranges_expression>.*?) )? }[\^@] 
                                                            (?P<comma_after>\s*,)?''')

# TODO: implement builtins correctly.
_FORTIEL_BUILTINS_NAMES = [
    '__INDEX__', '__FILE__', '__LINE__', '__DATE__', '__TIME__']


class FortielExecutor:
    """Fortiel syntax tree executor."""
    def __init__(self, options: FortielOptions):
        self._scope: Dict[str, Any] = {}
        self._macros: Dict[str, FortielMacroNode] = {}
        self._imported_files_paths: Set[str] = set()
        self._options: FortielOptions = options

    def _defined(self, name: str) -> bool:
        return name in self._scope

    @property
    def _loop_index(self) -> Optional[int]:
        return self._scope.get('__LOOP_INDEX__')

    @_loop_index.setter
    def _loop_index(self, index: Optional[int]) -> None:
        self._scope['__LOOP_INDEX__'] = index

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def _evaluate_expression(self, expression: str, file_path: str, line_number: int) -> Any:
        """Evaluate Python expression."""
        try:
            self._scope.update(__FILE__=file_path, __LINE__=line_number)
            value = eval(expression, self._scope)
            return value
        except Exception as error:
            error_text = str(error)
            error_text = error_text.replace('<head>', f'expression `{expression}`')
            error_text = error_text.replace('<string>', f'expression `{expression}`')
            message = f'Python expression evaluation error: {error_text}'
            raise FortielRuntimeError(message, file_path, line_number) from error

    def _evaluate_ranges_expression(
            self, expression: str, file_path: str, line_number: int) -> range:
        """Evaluate Python ranges expression"""
        ranges = self._evaluate_expression(expression, file_path, line_number)
        if not (isinstance(ranges, tuple) and (2 <= len(ranges) <= 3) and
                list(map(type, ranges)) == len(ranges) * [int]):
            message = \
                'tuple of two or three integers inside the <do> ' + \
                f'directive ranges is expected, got `{expression}`'
            raise FortielRuntimeError(message, file_path, line_number)
        (start, stop), step = ranges[0:2], (ranges[2] if len(ranges) == 3 else 1)
        return range(start, stop + step, step)

    def _evaluate_line(self, line: str, file_path: str, line_number: int) -> str:
        """Execute in-line substitutions."""

        def _evaluate_inline_loop_expression_sub(match: Match[str]) -> str:
            # Evaluate <^..>, <^{..}^> and <^{..^|^..}^> substitutions.
            expression, comma_before, comma_after = \
                match.group('expression', 'comma_before', 'comma_after')
            ranges_expression = match.groupdict().get('ranges_expression')
            if ranges_expression is not None:
                ranges = self._evaluate_ranges_expression(
                    ranges_expression, file_path, line_number)
            else:
                if (index := self._loop_index) is None:
                    message = '<^{..}^> rangeless substitution outside of the <do> loop body'
                    raise FortielRuntimeError(message, file_path, line_number)
                ranges = range(1, max(0, index) + 1)
            sub = ','.join([expression.replace('$$', str(i)) for i in ranges])
            if len(sub) > 0:
                if comma_before is not None:
                    sub = comma_before + sub
                if comma_after is not None:
                    sub += comma_after
            else:
                sub = ',' if (comma_before is not None) and (comma_after is not None) else ''
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
        # Special case for OpenMP/OpenACC directives:
        if line.lstrip().startswith('!$'):
            processed_lines = []
            for pragma_line in line.splitlines():
                cut = len(pragma_line) - len(pragma_line.lstrip().removeprefix('!$'))
                processed_lines.append(
                    pragma_line[:cut] +
                    _FORTIEL_INLINE_SHORT_EVAL.sub(
                        _evaluate_inline_eval_expression_sub, pragma_line[cut:]))
            line = '\n'.join(processed_lines)
        else:
            line = _FORTIEL_INLINE_SHORT_EVAL.sub(_evaluate_inline_eval_expression_sub, line)

        # Output the processed line.
        return line

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def execute_tree(self, tree: FortielTree, print_func: FortielPrintFunc) -> None:
        """Execute the syntax tree or the syntax tree node."""
        # Print primary line marker.
        if self._options.line_marker_format == 'fpp':
            print_func(f'# 1 "{tree.file_path}" 1')
        elif self._options.line_marker_format == 'cpp':
            print_func(f'#line 1 "{tree.file_path}" 1')
        # Execute tree nodes.
        self._execute_node_list(tree.root_nodes, print_func)

    def _execute_node(self, node: FortielNode, print_func: FortielPrintFunc) -> None:
        """Execute a node."""
        for nodeType, func in {
                FortielUseNode: self._execute_use_node,
                FortielLetNode: self._execute_let_node,
                FortielDelNode: self._execute_del_node,
                FortielIfNode: self._execute_if_node,
                FortielDoNode: self._execute_do_node,
                FortielForNode: self._execute_for_node,
                FortielMacroNode: self._execute_macro_node,
                FortielCallNode: self._execute_call_node,
                FortielLineListNode: self._execute_line_list_node}.items():
            if isinstance(node, nodeType):
                func = cast(Callable[[FortielNode, FortielPrintFunc], None], func)
                return func(node, print_func)
        node_type = type(node).__name__
        raise RuntimeError(f'internal error: no evaluator for directive type {node_type}')

    def _execute_node_list(self, nodes: List[FortielNode], print_func: FortielPrintFunc) -> None:
        """Execute the node list."""
        index = 0
        while index < len(nodes):
            if isinstance(nodes[index], FortielCallSegmentNode):
                # List of nodes could be modified during the call.
                self._resolve_call_segment(index, nodes)
                self._execute_call_node(cast(FortielCallNode, nodes[index]), print_func)
            else:
                self._execute_node(nodes[index], print_func)
            index += 1

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def _execute_line_list_node(
            self, node: FortielLineListNode, print_func: FortielPrintFunc) -> None:
        """Execute line block."""
        # Print line marker.
        if self._options.line_marker_format == 'fpp':
            print_func(f'# {node.line_number} "{node.file_path}"')
        elif self._options.line_marker_format == 'cpp':
            print_func(f'#line {node.line_number} "{node.file_path}"')
        # Print lines.
        for line_number, line in enumerate(node.lines, node.line_number):
            print_func(self._evaluate_line(line, node.file_path, line_number))

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def _execute_use_node(self, node: FortielUseNode, _: FortielPrintFunc) -> None:
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
            self.execute_tree(imported_tree, lambda _: None)

    def _execute_let_node(self, node: FortielLetNode, _: FortielPrintFunc) -> None:
        """Execute LET node."""
        # Check if the variable is not already defined, and is not a build-in name.
        if node.name in _FORTIEL_BUILTINS_NAMES:
            message = f'builtin name <{node.name}> can not be redefined'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        if node.arguments is None:
            # Evaluate variable.
            self._scope[node.name] = self._evaluate_expression(
                node.value_expression, node.file_path, node.line_number)
        else:
            # Evaluate variable as lambda function.
            function_expression = f'lambda {",".join(node.arguments)}: {node.value_expression}'
            function = self._evaluate_expression(
                function_expression, node.file_path, node.line_number)
            self._scope[node.name] = function

    def _execute_del_node(self, node: FortielDelNode, _: FortielPrintFunc) -> None:
        """Execute DEL node."""
        for name in node.names:
            if name not in self._scope:
                message = f'name `{name}` was not previously defined'
                raise FortielRuntimeError(message, node.file_path, node.line_number)
            if name in _FORTIEL_BUILTINS_NAMES:
                message = f'builtin name <{name}> can not be undefined'
                raise FortielRuntimeError(message, node.file_path, node.line_number)
            del self._scope[name]

    def _execute_if_node(self, node: FortielIfNode, print_func: FortielPrintFunc) -> None:
        """Execute IF/ELSE IF/ELSE/END IF node."""
        # Evaluate condition and execute THEN branch.
        condition = self._evaluate_expression(
            node.condition_expression, node.file_path, node.line_number)
        if condition:
            self._execute_node_list(node.then_nodes, print_func)
        else:
            # Evaluate condition and execute ELSE IF branches.
            for elif_node in node.elif_nodes:
                condition = self._evaluate_expression(
                    elif_node.condition_expression, node.file_path, node.line_number)
                if condition:
                    self._execute_node_list(elif_node.then_nodes, print_func)
                    break
            else:
                # Execute ELSE branch.
                self._execute_node_list(node.else_nodes, print_func)

    def _execute_do_node(self, node: FortielDoNode, print_func: FortielPrintFunc) -> None:
        """Execute DO/END DO node."""
        # Evaluate loop ranges.
        ranges = self._evaluate_ranges_expression(
            node.ranges_expression, node.file_path, node.line_number)
        if len(ranges) > 0:
            # Save previous index value
            # in case we are inside the nested loop.
            prev_index = self._loop_index
            for index in ranges:
                # Execute loop body.
                self._loop_index = self._scope[node.index_name] = index
                self._execute_node_list(node.loop_nodes, print_func)
            del self._scope[node.index_name]
            # Restore previous index value.
            self._loop_index = prev_index

    def _execute_for_node(self, node: FortielForNode, print_func: FortielPrintFunc) -> None:
        """Execute FOR/END FOR node."""
        # Evaluate loop.
        iterable: Iterable[Any] = self._evaluate_expression(
            node.iterable_expression, node.file_path, node.line_number)
        for index_values in iterable:
            if len(node.index_names) == 1:
                self._scope[node.index_names[0]] = index_values
            else:
                for index_name, index_value in zip(node.index_names, index_values):
                    self._scope[index_name] = index_value
            self._execute_node_list(node.loop_nodes, print_func)
        for index_name in node.index_names:
            del self._scope[index_name]

    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #
    # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

    def _execute_macro_node(self, node: FortielMacroNode, _: FortielPrintFunc) -> None:
        """Execute MACRO/END MACRO node."""
        if node.name in self._macros:
            message = f'macro `{node.name}` is already defined'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        if len(node.section_nodes) > 0:
            # TODO: refactor me
            section_names = node.section_names
            if node.name in section_names:
                message = f'section name cannot be the same with macro `{node.name}` name'
                raise FortielRuntimeError(message, node.file_path, node.line_number)
            if (dup := _find_duplicate(section_names)) is not None:
                message = f'duplicate section `{dup}` of the macro construct `{node.name}`'
                raise FortielRuntimeError(message, node.file_path, node.line_number)
        # Add macro to the scope.
        self._macros[node.name] = node

    def _resolve_call_segment(self, index: int, nodes: List[FortielNode]) -> None:
        """Resolve call segments."""
        node = cast(FortielCallSegmentNode, nodes[index])
        if (macro_node := self._macros.get(node.name)) is None:
            message = f'macro `{node.name}` was not previously defined'
            raise FortielRuntimeError(message, node.file_path, node.line_number)
        # Convert current node to call node and replace it in the node list.
        node = nodes[index] = FortielCallNode(node)
        end_name = 'end' + node.name
        if macro_node.is_construct:
            # Pop and process nodes until the end of macro construct call is reached.
            next_index = index + 1
            while len(nodes) > next_index:
                next_node = nodes[next_index]
                if isinstance(next_node, FortielCallSegmentNode):
                    if next_node.name == end_name:
                        nodes.pop(next_index)
                        break
                    if next_node.name in macro_node.section_names:
                        call_section_node = FortielCallSectionNode(next_node)
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

    def _execute_call_node(self, node: FortielCallNode, print_func: FortielPrintFunc) -> None:
        """Execute CALL node."""

        # Use a special print function
        # in order to keep indentations from the original source.
        # ( Note that we have to keep line markers not indented. )
        def _spaced_print_func(line: str):
            print_func(line if line.lstrip().startswith('#') else node.spaces_before + line)

        macro_node = self._macros[node.name]
        self._execute_pattern_list_node(node, macro_node, _spaced_print_func)
        # Match and evaluate macro sections.
        if macro_node.is_construct:
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
                self._execute_pattern_list_node(
                    call_section_node, section_node, _spaced_print_func)
                self._execute_node_list(call_section_node.captured_nodes, print_func)
                # Advance a section for sections with 'once' attribute.
                if section_node.once:
                    section_node = next(section_iterator, None)
            # Execute finally section.
            self._execute_node_list(macro_node.finally_nodes, _spaced_print_func)

    def _execute_pattern_list_node(
            self, node: Union[FortielCallNode, FortielCallSectionNode],
            macro_node: Union[FortielMacroNode, FortielSectionNode],
            print_func: FortielPrintFunc) -> None:
        # Find a match in macro or section patterns and
        # execute macro primary section or current section.
        for pattern_node in macro_node.pattern_nodes:
            if (match := pattern_node.pattern.match(node.argument)) is not None:
                self._scope |= match.groupdict()
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
        file_path: str, output_file_path: Optional[str],
        options: FortielOptions = FortielOptions()) -> None:
    """Preprocess the source file."""
    # Read the input file and parse it.
    with open(file_path, 'r') as file:
        lines = file.read().splitlines()
    tree = FortielParser(file_path, lines).parse()
    # Execute parse tree and print to output file.
    executor = FortielExecutor(options)
    if output_file_path is None:
        executor.execute_tree(tree, print)
    else:
        with open(output_file_path, 'w') as output_file:
            executor.execute_tree(tree, lambda line: print(line, file=output_file))


def main() -> None:
    """Fortiel entry point."""
    # Make CLI description and parse it.
    arg_parser = argparse.ArgumentParser()
    # Preprocessor definitions.
    arg_parser.add_argument(
        '-D', '--define', metavar='name[=value]', action='append', dest='defines', default=[],
        help='define a named variable')
    # Preprocessor include directories.
    arg_parser.add_argument(
        '-I', '--include', metavar='include_dir', action='append', dest='include_dirs', default=[],
        help='add an include directory path')
    # Line marker format.
    arg_parser.add_argument(
        '-M', '--line_markers', choices=['fpp', 'cpp', 'none'],
        default=FortielOptions().line_marker_format, help='line markers format')
    # Input and output file paths.
    arg_parser.add_argument(
        'file_path', help='input file path')
    arg_parser.add_argument(
        '-o', '--output_file_path', default=None, help='output file path')
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
