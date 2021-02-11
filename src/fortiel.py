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


"""
Fortiel language compiler and executor.
"""

import re
import argparse
from os import path

from typing import (cast, List, Set, Dict, Tuple, Any, Union,
                    Optional, Callable, Literal, Pattern, Match)


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #
# +-+-+                                                       +-+-+ #
# +-+-+                Fortiel Helper Routines                +-+-+ #
# +-+-+                                                       +-+-+ #
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #


def _regExpr(pattern: str) -> Pattern[str]:
  """Compile regular expression."""
  return re.compile(pattern, re.IGNORECASE)


def _makeName(name: str) -> str:
  """Compile a single-word lower case identifier."""
  return re.sub(r'\s*', '', name.lower())


def _findFile(filePath: str, dirPaths: List[str]) -> Optional[str]:
  """Find file in the directory list."""
  filePath = path.expanduser(filePath)
  if path.exists(filePath):
    return path.abspath(filePath)
  for dirPath in dirPaths:
    filePathInDir = path.expanduser(path.join(dirPath, filePath))
    if path.exists(filePathInDir):
      return path.abspath(filePathInDir)
  here = path.abspath(path.dirname(__file__))
  filePathInDir = path.join(here, filePath)
  if path.exists(filePathInDir):
    return filePathInDir
  return None


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+            Fortiel Exceptions and Messages            +-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #


class TielError(Exception):
  """Fortiel compilation/execution error."""
  def __init__(self, message: str,
               filePath: str, lineNumber: int) -> None:
    super().__init__()
    self.message: str = message
    self.filePath: str = filePath
    self.lineNumber: int = lineNumber

  def __str__(self) -> str:
    message = f'{self.filePath}:{self.lineNumber}:1:\n\n' \
              + f'Fatal Error: {self.message}'
    return message


class TielSyntaxError(TielError):
  """Directive syntax error."""
  def __init__(self, message: str,
               filePath: str, lineNumber: int) -> None:
    super(TielSyntaxError, self).__init__(
      f'syntax error: {message}', filePath, lineNumber)


class TielRuntimeError(TielError):
  """Error in the directive or line substitution evaluation."""
  def __init__(self, message: str,
               filePath: str, lineNumber: int) -> None:
    super(TielRuntimeError, self).__init__(
      f'runtime error: {message}', filePath, lineNumber)


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+                    Fortiel Options                    +-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #


class TielOptions:
  """Preprocessor options."""
  def __init__(self) -> None:
    self.defines: List[str] = []
    self.includePaths: List[str] = []
    self.lineMarkerFormat: Literal['fpp', 'cpp', 'none'] = 'none'


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+          Fortiel Lexer and Directives Parser          +-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #


_DIRECTIVE = _regExpr(r'^\s*#@\s*(?P<directive>.*)?$')
_DIR_HEAD = _regExpr(r'^(?P<word>[^\s]+)(\s+(?P<word2>[^\s]+))?')

SYNTAX_USE = _regExpr(r'^use\s+(?P<path>(\".+\")|(\'.+\')|(\<.+\>))$')

SYNTAX_LET = _regExpr(r'^let\s+(?P<name>[_a-zA-Z]\w*)\s*'
                      + r'(?P<arguments>\((?:\*{0,2}[_a-zA-Z]\w*'
                      + r'(\s*,\s*\*{0,2}[_a-zA-Z]\w*)*)?\s*\))?\s*'
                      + r'=\s*(?P<expression>.*)$')

SYNTAX_DEL = _regExpr(r'^del\s+(?P<names>[_a-zA-Z]\w*(\s*,\s*[a-zA-Z_]\w*)*)$')

SYNTAX_IF = _regExpr(r'^if\s*(?P<condition>.+)\s*:?$')
SYNTAX_ELSEIF = _regExpr(r'^else\s*if\s*(?P<condition>.+)\s*:?$')
SYNTAX_ELSE = _regExpr(r'^else$')
SYNTAX_ENDIF = _regExpr(r'^end\s*if$')

SYNTAX_DO = _regExpr(r'^do\s+(?P<index>[a-zA-Z_]\w*)\s*=\s*(?P<bounds>.*)\s*:?$')
SYNTAX_ENDDO = _regExpr(r'^end\s*do$')

SYNTAX_MACRO = _regExpr(r'^macro\s+(?P<name>[a-zA-Z]\w*)(\s+(?P<pattern>\^.*\$))?$')
SYNTAX_PATTERN = _regExpr(r'^pattern\s+(?P<pattern>\^.*\$)$')
SYNTAX_SECTION = _regExpr(r'^section\s+(?P<once>once\s+)?'
                          + r'(?P<name>[a-zA-Z]\w*)(\s+(?P<pattern>.*))?$')
SYNTAX_FINALLY = _regExpr(r'^finally$')
SYNTAX_ENDMACRO = _regExpr(r'^end\s*macro$')

SYNTAX_CALL = _regExpr(r'^(?P<spaces>\s*)'
                       + r'@(?P<name>(?:end\s*|else\s*)?[a-zA-Z]\w*)\b'
                       + r'(?P<argument>[^!]*)(\s*!.*)?$')


_MISPLACED_HEADS \
  = [_makeName(head)
     for head in ['else', 'else if', 'end if', 'end do',
                  'section', 'finally', 'pattern', 'end macro']]

_BUILTIN_HEADERS = {'.f90': 'tiel/syntax.fd'}

class TielTree:
  """Fortiel syntax tree."""
  def __init__(self, filePath: str) -> None:
    self.filePath: str = filePath
    self.rootNodes: List[TielNode] = []
    self.mutators: List[Tuple[Pattern[str], str]] = []


class TielNode:
  """Fortiel syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    self.filePath: str = filePath
    self.lineNumber: int = lineNumber


class TielNodeLineList(TielNode):
  """The list of code lines syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.lines: List[str] = []


class TielNodeUse(TielNode):
  """The USE directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.usedFilePath: str = ''


class TielNodeLet(TielNode):
  """The LET directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.arguments: Optional[str] = None
    self.expression: str = ''


class TielNodeDel(TielNode):
  """The DEL directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.names: List[str] = []


class TielNodeIf(TielNode):
  """The IF/ELSE IF/ELSE/END IF directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.condition: str = ''
    self.thenNodes: List[TielNode] = []
    self.elseIfNodes: List[TielNodeElseIf] = []
    self.elseNodes: List[TielNode] = []


class TielNodeElseIf(TielNode):
  """The ELSE IF directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.condition: str = ''
    self.branchNodes: List[TielNode] = []


class TielNodeDo(TielNode):
  """The DO/END DO directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.indexName: str = ''
    self.bounds: str = ''
    self.loopNodes: List[TielNode] = []


class TielNodeMacro(TielNode):
  """The MACRO/END MACRO directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.patternNodes: List[TielNodePattern] = []
    self.sectionNodes: List[TielNodeSection] = []
    self.finallyNodes: List[TielNode] = []

  def isConstruct(self) -> bool:
    """Is current macro a construct."""
    return len(self.sectionNodes) > 0 \
           or len(self.finallyNodes) > 0

  def sectionNames(self) -> List[str]:
    """Get a list of the section names."""
    return [node.name for node in self.sectionNodes]


class TielNodeSection(TielNode):
  """The SECTION directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.once: bool = False
    self.patternNodes: List[TielNodePattern] = []


class TielNodePattern(TielNode):
  """The PATTERN directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.pattern: Union[str, Pattern[str]] = ''
    self.matchNodes: List[TielNode] = []


class TielNodeCallSegment(TielNode):
  """The call segment syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.spaces: str = ''
    self.name: str = ''
    self.argument: str = ''


class TielNodeCall(TielNode):
  """The call directive syntax tree node."""
  def __init__(self, node: TielNodeCallSegment) -> None:
    super().__init__(node.filePath, node.lineNumber)
    self.spaces: str = node.spaces
    self.name: str = node.name
    self.argument: str = node.argument
    self.capturedNodes: List[TielNode] = []
    self.callSectionNodes: List[TielNodeCallSection] = []


class TielNodeCallSection(TielNode):
  """The call directive section syntax tree node."""
  def __init__(self, node: TielNodeCallSegment) -> None:
    super().__init__(node.filePath, node.lineNumber)
    self.name: str = node.name
    self.argument: str = node.argument
    self.capturedNodes: List[TielNode] = []


class TielParser:
  """Fortiel syntax tree parser."""
  def __init__(self, filePath: str, lines: List[str]) -> None:
    self._filePath: str = filePath
    self._lines: List[str] = lines
    self._currentLine: str = self._lines[0]
    self._currentLineIndex: int = 0
    self._currentLineNumber: int = 1

  def _matchesEnd(self) -> bool:
    return self._currentLineIndex >= len(self._lines)

  def _advanceLine(self) -> None:
    self._currentLineIndex += 1
    self._currentLineNumber += 1
    if self._matchesEnd():
      self._currentLine = ''
    else:
      self._currentLine = self._lines[self._currentLineIndex].rstrip()

  def _matchesLine(self, *patterns: Pattern[str]) -> Optional[Match[str]]:
    if self._matchesEnd():
      message = 'unexpected end of file'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    for pattern in patterns:
      match = pattern.match(self._currentLine)
      if match is not None:
        return match
    return None

  def _parseLineContinuation(self) -> None:
    """Parse continuation lines."""
    while self._currentLine.endswith('&'):
      self._currentLine: str = self._currentLine[:-1] + ' '
      self._currentLineIndex += 1
      self._currentLineNumber += 1
      if self._matchesEnd():
        message = 'unexpected end of file in continuation lines'
        raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
      nextLine = self._lines[self._currentLineIndex].lstrip()
      if nextLine.startswith('&'):
        nextLine = nextLine[1:].lstrip()
      self._currentLine += nextLine.rstrip()

  def parse(self) -> TielTree:
    """Parse the source lines."""
    tree = TielTree(self._filePath)
    # Add builtin headers based on file extension.
    _, fileExt = path.splitext(self._filePath)
    builtinPath = _BUILTIN_HEADERS.get(fileExt.lower())
    if builtinPath is not None:
      useBuiltinNode = TielNodeUse(self._filePath,
                            self._currentLineNumber)
      useBuiltinNode.usedFilePath = builtinPath
      tree.rootNodes.append(useBuiltinNode)
    # Parse file contents.
    while not self._matchesEnd():
      tree.rootNodes.append(self._parseStatement())
    return tree

  @staticmethod
  def _parseHead(directive: Optional[str]) -> Optional[str]:
    # Empty directives does not have a head.
    if directive is None or directive == '':
      return None
    # ELSE is merged with IF,
    # END is merged with any following word.
    dirHeadWord, dirHeadWord2 \
      = _DIR_HEAD.match(directive).group('word', 'word2')
    dirHead = dirHeadWord.lower()
    if dirHeadWord2 is not None:
      dirHeadWord2 = dirHeadWord2.lower()
      if dirHeadWord == 'end' or dirHeadWord == 'else' and dirHeadWord2 == 'if':
        dirHead += dirHeadWord2
    return dirHead

  def _parseStatement(self) -> TielNode:
    """Parse a directive or a line list."""
    if self._matchesLine(_DIRECTIVE):
      return self._parseDirective()
    if self._matchesLine(SYNTAX_CALL):
      self._parseLineContinuation()
      return self._parseDirectiveCall()
    return self._parseLineList()

  def _parseLineList(self) -> TielNodeLineList:
    """Parse a line list."""
    node = TielNodeLineList(
      self._filePath, self._currentLineNumber)
    while True:
      node.lines.append(self._currentLine)
      self._advanceLine()
      if self._matchesEnd() or self._matchesLine(_DIRECTIVE, SYNTAX_CALL):
        break
    return node

  def _parseDirective(self) -> TielNode:
    """Parse a directive."""
    self._parseLineContinuation()
    directive = self._matchesLine(_DIRECTIVE)['directive']
    dirHead = type(self)._parseHead(directive)
    if dirHead == 'use':
      return self._parseDirectiveUse()
    if dirHead == 'let':
      return self._parseDirectiveLet()
    if dirHead == 'del':
      return self._parseDirectiveDel()
    if dirHead == 'if':
      return self._parseDirectiveIf()
    if dirHead == 'do':
      return self._parseDirectiveDo()
    if dirHead == 'macro':
      return self._parseDirectiveMacro()
    # Determine the error type:
    # either the known directive is misplaced,
    # either the directive is unknown.
    if dirHead is None:
      message = 'empty directive'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    elif dirHead in _MISPLACED_HEADS:
      message = f'misplaced directive <{dirHead}>'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    else:
      message = f'unknown or mistyped directive <{dirHead}>'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)

  def _matchesDirectiveHead(self, *dirHeadList: str) -> Optional[str]:
    dirMatch = self._matchesLine(_DIRECTIVE)
    if dirMatch is not None:
      # Parse continuations and rematch.
      self._parseLineContinuation()
      dirMatch = self._matchesLine(_DIRECTIVE)
      directive = dirMatch['directive'].lower()
      dirHead = type(self)._parseHead(directive)
      if dirHead in [_makeName(head) for head in dirHeadList]:
        return dirHead
    return None

  def _matchDirectiveSyntax(self,
                            pattern: Pattern[str],
                            *groups: str) -> Union[str, Tuple[str, ...]]:
    directive = self._matchesLine(_DIRECTIVE)['directive'].rstrip()
    match = pattern.match(directive)
    if match is None:
      dirHead = type(self)._parseHead(directive)
      message = f'invalid <{dirHead}> directive syntax'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    self._advanceLine()
    return match.group(*groups)

  def _parseDirectiveUse(self) -> TielNodeUse:
    """Parse USE directive."""
    node = TielNodeUse(self._filePath, self._currentLineNumber)
    node.usedFilePath \
      = self._matchDirectiveSyntax(SYNTAX_USE, 'path')
    node.usedFilePath = node.usedFilePath[1:-1]
    return node

  def _parseDirectiveLet(self) -> TielNodeLet:
    """Parse LET directive."""
    # Note that we are not
    # evaluating or validating define arguments and body here.
    node = TielNodeLet(self._filePath, self._currentLineNumber)
    node.name, node.arguments, node.expression \
      = self._matchDirectiveSyntax(SYNTAX_LET,
                                   'name', 'arguments', 'expression')
    if node.arguments is not None:
      node.arguments = node.arguments[1:-1].strip()
    return node

  def _parseDirectiveDel(self) -> TielNodeDel:
    """Parse DEL directive."""
    # Note that we are not
    # evaluating or validating define name here.
    node = TielNodeDel(self._filePath, self._currentLineNumber)
    names = self._matchDirectiveSyntax(SYNTAX_DEL, 'names')
    node.names = [name.strip() for name in names.split(',')]
    return node

  def _parseDirectiveIf(self) -> TielNodeIf:
    """Parse IF/ELSE IF/ELSE/END IF directive."""
    # Note that we are not evaluating
    # or validating condition expressions here.
    node = TielNodeIf(self._filePath, self._currentLineNumber)
    node.condition = self._matchDirectiveSyntax(SYNTAX_IF, 'condition')
    while not self._matchesDirectiveHead('else if', 'else', 'end if'):
      node.thenNodes.append(self._parseStatement())
    if self._matchesDirectiveHead('else if'):
      while not self._matchesDirectiveHead('else', 'end if'):
        elseIfNode = TielNodeElseIf(self._filePath, self._currentLineNumber)
        elseIfNode.condition \
          = self._matchDirectiveSyntax(SYNTAX_ELSEIF, 'condition')
        while not self._matchesDirectiveHead('else if', 'else', 'end if'):
          elseIfNode.branchNodes.append(self._parseStatement())
        node.elseIfNodes.append(elseIfNode)
    if self._matchesDirectiveHead('else'):
      self._matchDirectiveSyntax(SYNTAX_ELSE)
      while not self._matchesDirectiveHead('end if'):
        node.elseNodes.append(self._parseStatement())
    self._matchDirectiveSyntax(SYNTAX_ENDIF)
    return node

  def _parseDirectiveDo(self) -> TielNodeDo:
    """Parse DO/END DO directive."""
    # Note that we are not evaluating
    # or validating loop bound expressions here.
    node = TielNodeDo(self._filePath, self._currentLineNumber)
    node.indexName, node.bounds \
      = self._matchDirectiveSyntax(SYNTAX_DO, 'index', 'bounds')
    while not self._matchesDirectiveHead('end do'):
      node.loopNodes.append(self._parseStatement())
    self._matchDirectiveSyntax(SYNTAX_ENDDO)
    return node

  def _parseDirectiveMacro(self) -> TielNodeMacro:
    """Parse MACRO/END MACRO directive."""
    node = TielNodeMacro(self._filePath, self._currentLineNumber)
    node.name, pattern \
      = self._matchDirectiveSyntax(SYNTAX_MACRO, 'name', 'pattern')
    node.name = _makeName(node.name)
    node.patternNodes \
      = self._parseDirectivePatternList(node, pattern)
    if self._matchesDirectiveHead('section'):
      while not self._matchesDirectiveHead('finally', 'end macro'):
        sectionNode = TielNodeSection(self._filePath, self._currentLineNumber)
        sectionNode.name, sectionNode.once, pattern \
          = self._matchDirectiveSyntax(SYNTAX_SECTION, 'name', 'once', 'pattern')
        sectionNode.name = _makeName(sectionNode.name)
        sectionNode.once = sectionNode.once is not None
        sectionNode.patternNodes \
          = self._parseDirectivePatternList(sectionNode, pattern)
        node.sectionNodes.append(sectionNode)
    if self._matchesDirectiveHead('finally'):
      self._matchDirectiveSyntax(SYNTAX_FINALLY)
      while not self._matchesDirectiveHead('end macro'):
        node.finallyNodes.append(self._parseStatement())
    self._matchDirectiveSyntax(SYNTAX_ENDMACRO)
    return node

  def _parseDirectivePatternList(self,
                                 node: Union[TielNodeMacro, TielNodeSection],
                                 pattern: str) -> List[TielNodePattern]:
    """Parse PATTERN directive list."""
    patternNodes: List[TielNodePattern] = []
    if pattern is not None:
      patternNode = TielNodePattern(node.filePath, node.lineNumber)
      patternNode.pattern = pattern
      while not self._matchesDirectiveHead('pattern', 'section',
                                           'finally', 'end macro'):
        patternNode.matchNodes.append(self._parseStatement())
      patternNodes.append(patternNode)
    elif not self._matchesDirectiveHead('pattern'):
      message = 'expected <pattern> directive'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    if self._matchesDirectiveHead('pattern'):
      while not self._matchesDirectiveHead('section',
                                           'finally', 'end macro'):
        patternNode = TielNodePattern(self._filePath, self._currentLineNumber)
        patternNode.pattern \
          = self._matchDirectiveSyntax(SYNTAX_PATTERN, 'pattern')
        while not self._matchesDirectiveHead('pattern', 'section',
                                             'finally', 'end macro'):
          patternNode.matchNodes.append(self._parseStatement())
        patternNodes.append(patternNode)
    # Compile the patterns.
    for patternNode in patternNodes:
      try:
        pattern = _regExpr(patternNode.pattern)
      except re.error as error:
        message = f'invalid pattern regular expression `{patternNode.pattern}`'
        raise TielSyntaxError(
          message, patternNode.filePath, patternNode.lineNumber) from error
      else:
        patternNode.pattern = pattern
    return patternNodes

  def _parseDirectiveCall(self) -> TielNodeCallSegment:
    """Parse call directive."""
    # Note that we are not evaluating
    # or matching call arguments and sections here.
    node = TielNodeCallSegment(self._filePath,
                               self._currentLineNumber)
    # Call directive uses different syntax,
    # so it cannot be parsed with common routines.
    match = self._matchesLine(SYNTAX_CALL)
    if match is None:
      message = f'invalid macro call syntax'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    self._advanceLine()
    node.spaces, node.name, node.argument \
      = match.group('spaces', 'name', 'argument')
    node.name = _makeName(node.name)
    node.argument = node.argument.strip()
    return node


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+              Fortiel Directives Executor              +-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #


_NAME_SUB = _regExpr(r'\$\s*(?P<name>[_a-zA-Z]\w*)\b')
_LINE_SUB = _regExpr(r'`(?P<expression>[^`]+)`')
_LOOP_SUB = _regExpr(r'@(?P<expression>:(\s*,)?)')

_BUILTIN_NAMES = ['__INDEX__',
                  '__FILE__', '__LINE__', '__DATE__', '__TIME__']


TielPrinter = Callable[[str], None]


class TielExecutor:
  """Fortiel syntax tree executor."""
  def __init__(self, options: TielOptions):
    self._scope: Dict[str, Any] = {}
    self._macros: Dict[str, TielNodeMacro] = {}
    self._usedFilePaths: Set[str] = set()
    self._options: TielOptions = options

  def execTree(self, tree: TielTree, printer: TielPrinter) -> None:
    """Execute the syntax tree or the syntax tree node."""
    # Print primary line marker.
    if self._options.lineMarkerFormat == 'fpp':
      printer(f'# 1 "{tree.filePath}" 1')
    elif self._options.lineMarkerFormat == 'cpp':
      printer(f'#line 1 "{tree.filePath}" 1')
    # Execute tree nodes.
    self._execNodeList(tree.rootNodes, printer)

  def _execNodeList(self, nodes: List[TielNode], printer: TielPrinter) -> None:
    """Execute the node list."""
    index = 0
    while index < len(nodes):
      if isinstance(nodes[index], TielNodeCallSegment):
        self._resolveCallSegment(index, nodes)
      self._execNode(nodes[index], printer)
      index += 1

  def _resolveCallSegment(self, index: int, nodes: List[TielNode]) -> None:
    """Resolve call segments."""
    node = cast(TielNodeCallSegment, nodes[index])
    macroNode = self._macros.get(node.name)
    if macroNode is None:
      message = f'macro `{node.name}` was not previously defined'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    # Convert current node to call node
    # and replace it in the node list.
    node = nodes[index] = TielNodeCall(node)
    if macroNode.isConstruct():
      # Pop and process nodes until the
      # end of macro construct call is reached.
      nextIndex = index + 1
      endName = 'end' + node.name
      while len(nodes) > nextIndex:
        nextNode = nodes[nextIndex]
        if isinstance(nextNode, TielNodeCallSegment):
          if nextNode.name == endName:
            nodes.pop(nextIndex)
            break
          if nextNode.name in macroNode.sectionNames():
            callSectionNode = TielNodeCallSection(nextNode)
            node.callSectionNodes.append(callSectionNode)
            nodes.pop(nextIndex)
            continue
          # Resolve the scoped call.
          self._resolveCallSegment(nextIndex, nodes)
        # Append the current node
        # to the most recent section of the call node.
        nextNode = nodes.pop(nextIndex)
        if len(node.callSectionNodes) == 0:
          node.capturedNodes.append(nextNode)
        else:
          node.callSectionNodes[-1].capturedNodes.append(nextNode)
      else:
        message = f'expected `@{endName}` call segment'
        raise TielRuntimeError(message, node.filePath, node.lineNumber)

  def _evalPyExpr(self,
                  expression: str, filePath: str, lineNumber: int) -> Any:
    """Evaluate Python expression."""
    try:
      value = eval(expression, self._scope)
      return value
    except Exception as error:
      message = 'Python expression evaluation error: ' \
                + f'{str(error).replace("<head>", f"expression `{expression}`")}'
      raise TielRuntimeError(message, filePath, lineNumber) from error

  def _execNode(self, node: TielNode, printer: TielPrinter):
    """Execute a node."""
    if isinstance(node, TielNodeUse):
      return self._execNodeUse(node)
    if isinstance(node, TielNodeLet):
      return self._execNodeLet(node)
    if isinstance(node, TielNodeDel):
      return self._evalNodeDel(node)
    if isinstance(node, TielNodeIf):
      return self._execNodeIf(node, printer)
    if isinstance(node, TielNodeDo):
      return self._execNodeDo(node, printer)
    if isinstance(node, TielNodeMacro):
      return self._execNodeMacro(node)
    if isinstance(node, TielNodeCall):
      return self._execNodeCall(node, printer)
    if isinstance(node, TielNodeLineList):
      return self._execNodeLineList(node, printer)
    nodeType = type(node).__name__
    raise RuntimeError('internal error: '
                       + f'no evaluator for directive type {nodeType}')

  def _execLine(self, line: str, filePath: str, lineNumber: int, printer: TielPrinter) -> None:
    """Execute in-line substitutions."""
    # Skip comment lines
    # (TODO: no inline comments for now).
    if line.lstrip().startswith('!'):
      printer(line)
      return
    # Evaluate name substitutions.
    def _nameSubReplace(match: Match[str]) -> str:
      name = match['name']
      value = self._scope.get(name)
      if value is None:
        message = f'variable ${name} was not previously declared'
        raise TielRuntimeError(message, filePath, lineNumber)
      return str(value)
    line = _NAME_SUB.sub(_nameSubReplace, line)
    # Evaluate expression substitutions.
    def _lineSubReplace(match: Match[str]) -> str:
      expression = match['expression']
      return str(self._evalPyExpr(expression, filePath, lineNumber))
    line = _LINE_SUB.sub(_lineSubReplace, line)
    # Evaluate <@:> substitutions.
    def _loopSubReplace(match: Match[str]) -> str:
      expression = match['expression']
      index = self._scope.get('__INDEX__')
      if index is None:
        message = '<@:> substitution outside of the <do> loop body'
        raise TielRuntimeError(message, filePath, lineNumber)
      return str(index * expression)
    line = _LOOP_SUB.sub(_loopSubReplace, line)
    # Output the processed line.
    printer(line)

  def _execNodeLineList(self, node: TielNodeLineList, printer: TielPrinter) -> None:
    """Execute line block."""
    # Print line marker.
    if self._options.lineMarkerFormat == 'fpp':
      printer(f'# {node.lineNumber} "{node.filePath}"')
    elif self._options.lineMarkerFormat == 'cpp':
      printer(f'#line {node.lineNumber} "{node.filePath}"')
    # Print lines.
    for lineNumber, line in enumerate(node.lines, start=node.lineNumber):
      self._execLine(line, node.filePath, lineNumber, printer)

  def _execNodeUse(self, node: TielNodeUse) -> None:
    """Execute USE node."""
    # Resolve file path.
    nodeDirPath = path.dirname(node.filePath)
    usedFilePath = _findFile(node.usedFilePath,
                             self._options.includePaths + [nodeDirPath])
    if usedFilePath is None:
      message = f'`{node.usedFilePath}` was not found in the include paths'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    # Ensure that file is used only once.
    if usedFilePath not in self._usedFilePaths:
      self._usedFilePaths.add(usedFilePath)
      try:
        with open(usedFilePath, mode='r') as usedFile:
          usedFileLines = usedFile.read().splitlines()
      except IsADirectoryError as error:
        message = f'`{node.usedFilePath}` is a directory'
        raise TielRuntimeError(message, node.filePath, node.lineNumber) from error
      except IOError as error:
        message = f'unable to read file `{node.usedFilePath}`'
        raise TielRuntimeError(message, node.filePath, node.lineNumber) from error
      # Parse and execute the dependency.
      # ( Use a dummy printer in order to skip code lines. )
      usedTree = TielParser(node.usedFilePath, usedFileLines).parse()
      def _dummyPrinter(_: str): pass
      self.execTree(usedTree, _dummyPrinter)

  def _execNodeLet(self, node: TielNodeLet) -> None:
    """Execute LET node."""
    # Check if the variable is not already defined,
    # and is not a build-in name.
    if node.name in self._scope:
      message = f'name `{node.name}` is already defined'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    if node.name in _BUILTIN_NAMES:
      message = f'builtin name <{node.name}> can not be redefined'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    if node.arguments is None:
      # Evaluate variable.
      value = self._evalPyExpr(node.expression,
                               node.filePath, node.lineNumber)
      self._scope[node.name] = value
    else:
      # Evaluate variable as lambda function.
      argNames = [arg.strip()
                  for arg in node.arguments.split(',')]
      if len(argNames) > len(set(argNames)):
        message = 'functional <let> arguments must be unique'
        raise TielRuntimeError(message, node.filePath, node.lineNumber)
      expression = f'lambda {node.arguments}: {node.expression}'
      function = self._evalPyExpr(expression,
                                  node.filePath, node.lineNumber)
      self._scope[node.name] = function

  def _evalNodeDel(self, node: TielNodeDel) -> None:
    """Execute DEL node."""
    for name in node.names:
      if name not in self._scope:
        message = f'name `{name}` was not previously defined'
        raise TielRuntimeError(message, node.filePath, node.lineNumber)
      if name in _BUILTIN_NAMES:
        message = f'builtin name <{name}> can not be undefined'
        raise TielRuntimeError(message, node.filePath, node.lineNumber)
      del self._scope[name]

  def _execNodeIf(self, node: TielNodeIf, printer: TielPrinter) -> None:
    """Execute IF/ELSE IF/ELSE/END IF node."""
    # Evaluate condition and execute THEN branch.
    if self._evalPyExpr(node.condition,
                        node.filePath, node.lineNumber):
      self._execNodeList(node.thenNodes, printer)
    else:
      # Evaluate condition and execute ELSE IF branches.
      for elseIfNode in node.elseIfNodes:
        if self._evalPyExpr(elseIfNode.condition,
                            elseIfNode.filePath, elseIfNode.lineNumber):
          self._execNodeList(elseIfNode.branchNodes, printer)
          break
      else:
        # Execute ELSE branch.
        self._execNodeList(node.elseNodes, printer)

  def _execNodeDo(self, node: TielNodeDo, printer: TielPrinter) -> None:
    """Execute DO/END DO node."""
    # Evaluate loop bounds.
    bounds = self._evalPyExpr(node.bounds,
                              node.filePath, node.lineNumber)
    if not (isinstance(bounds, tuple)
            and (2 <= len(bounds) <= 3)
            and list(map(type, bounds)) == len(bounds) * [int]):
      message = 'tuple of two or three integers inside the <do> ' \
                + f'directive bounds is expected, got `{node.bounds}`'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    start, stop = bounds[0:2]
    step = bounds[2] if len(bounds) == 3 else 1
    # Save previous index value
    # in case we are inside the nested loop.
    prevIndex = self._scope.get('__INDEX__')
    for index in range(start, stop + 1, step):
      # Execute loop body.
      self._scope[node.indexName] = index
      self._scope['__INDEX__'] = index
      self._execNodeList(node.loopNodes, printer)
    del self._scope[node.indexName]
    # Restore previous index value.
    self._scope['__INDEX__'] = prevIndex

  def _execNodeMacro(self, node: TielNodeMacro) -> None:
    """Execute MACRO/END MACRO node."""
    if node.name in self._macros:
      message = f'macro `{node.name}` is already defined'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    if len(node.sectionNodes) > 0:
      sectionNames = node.sectionNames()
      if node.name in sectionNames:
        message = 'section name cannot be the same with macro name'
        raise TielRuntimeError(message, node.filePath, node.lineNumber)
      if len(sectionNames) != len(set(sectionNames)):
        message = 'section names must be unique'
        raise TielRuntimeError(message, node.filePath, node.lineNumber)
    # Add macro to the scope.
    self._macros[node.name] = node

  def _execNodeCall(self, node: TielNodeCall, printer: TielPrinter) -> None:
    """Execute CALL node."""
    macroNode = self._macros[node.name]
    # Use a special print function
    # in order to keep indentations from the original source.
    # ( Note that we have to keep line markers unindented. )
    def _spacedPrinter(line: str):
      printer(line if line.startswith('#') else node.spaces + line)
    self._execNodePatternList(node, macroNode, _spacedPrinter)
    # Match and evaluate macro sections.
    if macroNode.isConstruct():
      self._execNodeList(node.capturedNodes, printer)
      sectionIter = iter(macroNode.sectionNodes)
      sectionNode = next(sectionIter, None)
      for callSectionNode in node.callSectionNodes:
        # Find a section node match.
        while sectionNode is not None \
            and sectionNode.name != callSectionNode.name:
          sectionNode = next(sectionIter, None)
        if sectionNode is None:
          message = f'unexpected call section `{callSectionNode.name}`'
          raise TielRuntimeError(
            message, callSectionNode.filePath, callSectionNode.lineNumber)
        # Execute the section.
        self._execNodePatternList(callSectionNode,
                                  sectionNode, _spacedPrinter)
        self._execNodeList(callSectionNode.capturedNodes, printer)
        # Advance a section for sections with 'once' attribute.
        if sectionNode.once:
          sectionNode = next(sectionIter, None)
      # Execute finally section.
      self._execNodeList(macroNode.finallyNodes, _spacedPrinter)

  def _execNodePatternList(self,
                           node: Union[TielNodeCall, TielNodeCallSection],
                           macroNode: Union[TielNodeMacro, TielNodeSection],
                           printer: TielPrinter) -> None:
    # Find a match in macro or section patterns
    # and execute macro primary section or current section.
    for patternNode in macroNode.patternNodes:
      match = patternNode.pattern.match(node.argument)
      if match is not None:
        self._scope = {**self._scope, **match.groupdict()}
        self._execNodeList(patternNode.matchNodes, printer)
        break
    else:
      message = f'macro `{macroNode.name}` ' \
                + 'call does not match any pattern'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)


# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+              Fortiel API and Entry Point              +-+-+ #
# +-+-+-+-+-+                                           +-+-+-+-+-+ #
# +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ #


def tiel_preprocess(filePath: str,
                    outputFilePath: str,
                    options: TielOptions = TielOptions()) -> None:
  """Preprocess the source file."""
  with open(filePath, 'r') as file:
    lines = file.read().splitlines()
  tree: TielTree = TielParser(filePath, lines).parse()
  with open(outputFilePath, 'w') as outputFile:
    def _printer(line): print(line, file=outputFile)
    TielExecutor(options).execTree(tree, _printer)


def tiel_main() -> None:
  """Fortiel entry point."""
  # Make CLI description and parse it.
  argParser = \
    argparse.ArgumentParser()
  argParser.add_argument(
    '-D', '--define',
    action='append', dest='defines', default=[], metavar='NAME[=VALUE]',
    help='define a named variable')
  argParser.add_argument(
    '-I', '--include',
    action='append', dest='include_dirs', default=[], metavar='INCLUDE_DIR',
    help='add an include directory path')
  argParser.add_argument(
    '-N', '--line_markers',
    choices=['fpp', 'cpp', 'none'], default='fpp',
    help='line markers format')
  argParser.add_argument(
    'file_path',
    help='input file path')
  argParser.add_argument(
    'output_file_path',
    help='output file path')
  args = argParser.parse_args()
  # Get input and output file paths.
  filePath = args.file_path
  outputFilePath = args.output_file_path
  # Get other options.
  options = TielOptions()
  options.defines += args.defines
  options.includePaths += args.include_dirs
  options.lineMarkerFormat = args.line_markers
  tiel_preprocess(filePath, outputFilePath, options)


if __name__ == '__main__':
  tiel_main()