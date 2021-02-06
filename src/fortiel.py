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
Fortiel language compiler and executor.
"""

import re
import argparse
from os import path

from typing import (List, Set, Dict, Tuple, Any, cast,
                    Union, Optional, Callable, Pattern, Match)


def _regExpr(pattern: str) -> Pattern[str]:
  """Compile regular expression."""
  return re.compile(pattern, re.IGNORECASE)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


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
    super(self).__init__(
      f'syntax error: {message}', filePath, lineNumber)


class TielRuntimeError(TielError):
  """Error in the directive or line substitution evaluation."""
  def __init__(self, message: str,
               filePath: str, lineNumber: int) -> None:
    super(self).__init__(
      f'runtime error: {message}', filePath, lineNumber)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielOptions:
  """Preprocessor options.
  """
  def __init__(self) -> None:
    self.includePaths: List[str] = []


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_DIRECTIVE = _regExpr(r'^\s*#@\s*(?P<directive>.*)?$')
_DIR_HEAD = _regExpr(r'^(?P<word>[^\s]+)(\s+(?P<word2>[^\s]+))?')

_DIR_USE = _regExpr(r'^use\s+(?P<path>(\".+\")|(\'.+\')|(\<.+\>))$')

_DIR_LET = _regExpr(r'^let\s+(?P<name>[_a-zA-Z]\w*)\s*'
                    + r'(?P<arguments>\((?:\*{0,2}[_a-zA-Z]\w*'
                    + r'(\s*,\s*\*{0,2}[_a-zA-Z]\w*)*)?\s*\))?\s*'
                    + r'=\s*(?P<expression>.*)$')

_DIR_DEL = _regExpr(r'^del\s+(?P<names>[a-zA-Z_]\w*(\s*,\s*[a-zA-Z_]\w*)*)$')

_DIR_IF = _regExpr(r'^if\s*(?P<condition>.+)\s*:?$')
_DIR_ELSE_IF = _regExpr(r'^else\s*if\s*(?P<condition>.+)\s*:?$')
_DIR_ELSE = _regExpr(r'^else$')
_DIR_END_IF = _regExpr(r'^end\s*if$')

_DIR_DO = _regExpr(r'^do\s+(?P<index>[a-zA-Z_]\w*)\s*=\s*(?P<bounds>.*)\s*:?$')
_DIR_END_DO = _regExpr(r'^end\s*do$')

_DIR_MACRO = _regExpr(r'^macro\s+(?P<construct>construct\s+)?'
                      + r'(?P<name>[a-zA-Z]\w*)(\s+(?P<pattern>.*))?$')
_DIR_PATTERN = _regExpr(r'^pattern\s+(?P<pattern>.*)$')
_DIR_SECTION = _regExpr(r'^section\s+(?P<once>once\s+)?'
                        + r'(?P<name>[a-zA-Z]\w*)(\s+(?P<pattern>.*))?$')
_DIR_FINALLY = _regExpr(r'^finally$')
_DIR_END_MACRO = _regExpr(r'^end\s*macro$')

_CALL_SYNTAX = _regExpr(r'^(?P<spaces>\s*)'
                        + r'@(?P<name>(?:end\s*|else\s*)?[a-zA-Z]\w*)\b'
                        + r'(?P<argument>[^!]*)(\s*!.*)?$')

_MISPLACED_HEADS = [head.replace(' ', '')
                    for head in ['else', 'else if', 'end if', 'end do',
                                 'section', 'finally', 'pattern', 'end macro']]


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
    self.includedFilePath: str = ''
    self.doPrintLines: bool = False


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


class TielNodeIfEnd(TielNode):
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
    self.nodes: List[TielNode] = []


class TielNodeDoEnd(TielNode):
  """The DO/END DO directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.indexName: str = ''
    self.bounds: str = ''
    self.nodes: List[TielNode] = []


class TielNodeMacroEnd(TielNode):
  """The MACRO/END MACRO directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.construct: bool = False
    self.patternNodes: List[TielNodePattern] = []
    self.sectionNodes: Union[List[TielNodeSection],
                             Dict[str, TielNodeSection]] = []
    self.finallyNodes: List[TielNode] = []

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
    self.nodes: List[TielNode] = []


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
    self.construct: bool = False
    self.nodes: List[TielNode] = []
    self.sectionNodes: List[TielNodeCallSection] = []


class TielNodeCallSection(TielNode):
  """The call directive section syntax tree node."""
  def __init__(self, node: TielNodeCallSegment) -> None:
    super().__init__(node.filePath, node.lineNumber)
    self.name: str = node.name
    self.argument: str = node.argument
    self.nodes: List[TielNode] = []


class TielParser:
  """Preprocessor syntax tree parser.
  """
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

  def parse(self) -> TielTree:
    """Parse the source lines."""
    tree = TielTree(self._filePath)
    while not self._matchesEnd():
      tree.rootNodes.append(self._parseStatement())
    return tree

  def _parseStatement(self) -> TielNode:
    """Parse a directive or a line list."""
    if self._matchesLine(_DIRECTIVE):
      return self._parseDirective()
    if self._matchesLine(_CALL_SYNTAX):
      self._parseLineContinuation()
      return self._parseDirectiveCall()
    return self._parseLineList()

  def _parseLineList(self) -> TielNodeLineList:
    """Parse a line list."""
    node = TielNodeLineList(self._filePath,
                            self._currentLineNumber)
    while True:
      node.lines.append(self._currentLine)
      self._advanceLine()
      if self._matchesEnd() or self._matchesLine(_DIRECTIVE, _CALL_SYNTAX):
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
      return self._parseDirectiveIfEnd()
    if dirHead == 'do':
      return self._parseDirectiveDoEnd()
    if dirHead == 'macro':
      return self._parseDirectiveMacroEnd()
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
      if dirHead in [x.replace(' ', '') for x in dirHeadList]:
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
    node = TielNodeUse(self._filePath,
                       self._currentLineNumber)
    node.includedFilePath \
      = self._matchDirectiveSyntax(_DIR_USE, 'path')
    node.includedFilePath = node.includedFilePath[1:-1]
    return node

  def _parseDirectiveLet(self) -> TielNodeLet:
    """Parse LET directive."""
    # Note that we are not
    # evaluating or validating define arguments and body here.
    node = TielNodeLet(self._filePath,
                       self._currentLineNumber)
    node.name, node.arguments, node.expression \
      = self._matchDirectiveSyntax(_DIR_LET, 'name', 'arguments', 'expression')
    if node.arguments is not None:
      node.arguments = node.arguments[1:-1].strip()
    return node

  def _parseDirectiveDel(self) -> TielNodeDel:
    """Parse DEL directive."""
    # Note that we are not
    # evaluating or validating define name here.
    node = TielNodeDel(self._filePath,
                       self._currentLineNumber)
    names = self._matchDirectiveSyntax(_DIR_DEL, 'names')
    node.names = [name.strip() for name in names.split(',')]
    return node

  def _parseDirectiveIfEnd(self) -> TielNodeIfEnd:
    """Parse IF/ELSE IF/ELSE/END IF directive."""
    # Note that we are not evaluating
    # or validating condition expressions here.
    node = TielNodeIfEnd(self._filePath,
                         self._currentLineNumber)
    node.condition = self._matchDirectiveSyntax(_DIR_IF, 'condition')
    while not self._matchesDirectiveHead('else if', 'else', 'end if'):
      node.thenNodes.append(self._parseStatement())
    if self._matchesDirectiveHead('else if'):
      while not self._matchesDirectiveHead('else', 'end if'):
        elseIfNode = TielNodeElseIf(self._filePath,
                                    self._currentLineNumber)
        elseIfNode.condition \
          = self._matchDirectiveSyntax(_DIR_ELSE_IF, 'condition')
        while not self._matchesDirectiveHead('else if', 'else', 'end if'):
          elseIfNode.nodes.append(self._parseStatement())
        node.elseIfNodes.append(elseIfNode)
    if self._matchesDirectiveHead('else'):
      self._matchDirectiveSyntax(_DIR_ELSE)
      while not self._matchesDirectiveHead('end if'):
        node.elseNodes.append(self._parseStatement())
    self._matchDirectiveSyntax(_DIR_END_IF)
    return node

  def _parseDirectiveDoEnd(self) -> TielNodeDoEnd:
    """Parse DO/END DO directive."""
    # Note that we are not evaluating
    # or validating loop bound expressions here.
    node = TielNodeDoEnd(self._filePath,
                         self._currentLineNumber)
    node.indexName, node.bounds \
      = self._matchDirectiveSyntax(_DIR_DO, 'index', 'bounds')
    while not self._matchesDirectiveHead('end do'):
      node.nodes.append(self._parseStatement())
    self._matchDirectiveSyntax(_DIR_END_DO)
    return node

  def _parseDirectiveMacroEnd(self) -> TielNodeMacroEnd:
    """Parse MACRO/END MACRO directive."""
    node = TielNodeMacroEnd(self._filePath,
                            self._currentLineNumber)
    node.name, node.construct, pattern \
      = self._matchDirectiveSyntax(_DIR_MACRO, 'name', 'construct', 'pattern')
    node.name = node.name.lower()
    node.construct = node.construct is not None
    node.patternNodes \
      = self._parseSectionPatternList(node, pattern)
    if node.construct:
      if self._matchesDirectiveHead('section'):
        while not self._matchesDirectiveHead('finally', 'end macro'):
          sectionNode = TielNodeSection(self._filePath,
                                        self._currentLineNumber)
          sectionNode.name, sectionNode.once, pattern \
            = self._matchDirectiveSyntax(_DIR_SECTION, 'name', 'once', 'pattern')
          sectionNode.name = sectionNode.name.lower()
          sectionNode.once = sectionNode.once is not None
          sectionNode.patternNodes \
            = self._parseSectionPatternList(sectionNode, pattern)
          node.sectionNodes.append(sectionNode)
      if self._matchesDirectiveHead('finally'):
        self._matchDirectiveSyntax(_DIR_FINALLY)
        while not self._matchesDirectiveHead('end macro'):
          node.finallyNodes.append(self._parseStatement())
    self._matchDirectiveSyntax(_DIR_END_MACRO)
    return node

  def _parseSectionPatternList(self,
                               node: Union[TielNodeMacroEnd, TielNodeSection],
                               pattern: str) -> List[TielNodePattern]:
    """Parse PATTERN directive list."""
    patternNodes: List[TielNodePattern] = []
    if pattern is not None:
      patternNode = TielNodePattern(node.filePath,
                                    node.lineNumber)
      patternNode.pattern = pattern
      while not self._matchesDirectiveHead('pattern', 'section',
                                           'finally', 'end macro'):
        patternNode.nodes.append(self._parseStatement())
      patternNodes.append(patternNode)
    elif not self._matchesDirectiveHead('pattern'):
      message = 'expected <pattern> directive'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    if self._matchesDirectiveHead('pattern'):
      while not self._matchesDirectiveHead('section',
                                           'finally', 'end macro'):
        patternNode = TielNodePattern(self._filePath,
                                      self._currentLineNumber)
        patternNode.pattern \
          = self._matchDirectiveSyntax(_DIR_PATTERN, 'pattern')
        while not self._matchesDirectiveHead('pattern', 'section',
                                             'finally', 'end macro'):
          patternNode.nodes.append(self._parseStatement())
        patternNodes.append(patternNode)
    return patternNodes

  def _parseDirectiveCall(self) -> TielNodeCallSegment:
    """Parse call directive."""
    # Note that we are not evaluating
    # or matching call arguments and sections here.
    node = TielNodeCallSegment(self._filePath,
                               self._currentLineNumber)
    match = self._matchesLine(_CALL_SYNTAX)
    if match is None:
      message = f'invalid macro call syntax'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    self._advanceLine()
    node.spaces, node.name, node.argument \
      = match.group('spaces', 'name', 'argument')
    node.argument = node.argument.strip()
    return node


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_NAME_SUB = _regExpr(r'\$\s*(?P<name>[_a-zA-Z]\w*)\b')
_LINE_SUB = _regExpr(r'`(?P<expression>[^`]+)`')
_LOOP_SUB = _regExpr(r'@(?P<expression>:(\s*,)?)')

_BUILTIN_NAMES = ['__INDEX__',
                  '__FILE__', '__LINE__', '__DATE__', '__TIME__']


TielPrintFunc = Callable[[str], None]


class TielExecutor:
  """Preprocessor syntax tree executor.
  """
  def __init__(self, options: TielOptions):
    self._scope: Dict[str, Any] = {}
    self._scopeMacros: Dict[str, TielNodeMacroEnd] = {}
    self._channel: str = ''
    self._channeledLines: Dict[str, List[str]] = {}
    self._options: TielOptions = options

  def execTree(self, tree: TielTree, printFunc: TielPrintFunc) -> None:
    """Execute the syntax tree or the syntax tree node."""
    printFunc(f'# 1 "{tree.filePath}" 1')
    self._execNodeList(tree.rootNodes, printFunc)

  def _execNodeList(self, nodes: List[TielNode], printFunc: TielPrintFunc) -> None:
    """Execute the syntax tree node or a list of nodes."""
    nodes = list(nodes)
    while len(nodes) != 0:
      # Resolve the call segment and execute the cell.
      node = nodes.pop(0)
      if isinstance(node, TielNodeCallSegment):
        node, nodes = self._resolveCall(node, nodes)
        self._execNodeCallEnd(node, printFunc)
      # Execute the node.
      elif isinstance(node, TielNodeLineList):
        self._execLineList(node, printFunc)
      else:
        self._execDirective(node, printFunc)

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

  def _execLineList(self,
                    node: TielNodeLineList,
                    printFunc: TielPrintFunc) -> None:
    """Execute line block."""
    printFunc(f'# {node.lineNumber} "{node.filePath}"')
    for lineNumber, line in \
        enumerate(node.lines, start=node.lineNumber):
      self._execLine(line, node.filePath, lineNumber, printFunc)

  def _execLine(self, line: str, filePath: str, lineNumber: int,
                printFunc: TielPrintFunc) -> None:
    """Execute in-line substitutions."""
    # Skip comment lines
    # (no inline comments for now).
    if line.lstrip().startswith('!'):
      printFunc(line)
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
    line = re.sub(_LOOP_SUB, _loopSubReplace, line)
    # Output the processed line.
    printFunc(line)

  def _execDirective(self,
                     node: TielNode,
                     printFunc: TielPrintFunc):
    """Execute directive."""
    if isinstance(node, TielNodeUse):
      return self._execNodeUse(node, printFunc)
    if isinstance(node, TielNodeLet):
      return self._execNodeLet(node)
    if isinstance(node, TielNodeDel):
      return self._evalNodeDel(node)
    if isinstance(node, TielNodeIfEnd):
      return self._execNodeIfEnd(node, printFunc)
    if isinstance(node, TielNodeDoEnd):
      return self._execNodeDoEnd(node, printFunc)
    if isinstance(node, TielNodeMacroEnd):
      return self._execNodeMacroEnd(node)
    if isinstance(node, TielNodeCall):
      return self._execNodeCallEnd(node, printFunc)
    nodeType = type(node).__name__
    raise RuntimeError('internal error: '
                       + f'no evaluator for directive type {nodeType}')

  @staticmethod
  def _findFile(filePath: str, dirPaths: List[str]) -> Optional[str]:
    filePath = path.expanduser(filePath)
    if path.exists(filePath):
      return filePath
    for dirPath in dirPaths:
      filePathInDir = path.expanduser(path.join(dirPath, filePath))
      if path.exists(filePathInDir):
        return filePathInDir
    here = path.abspath(path.dirname(__file__))
    filePathInDir = path.join(here, filePath)
    if path.exists(filePathInDir):
      return filePathInDir
    return None

  def _execNodeUse(self, node: TielNodeUse, printFunc: TielPrintFunc) -> None:
    """Execute USE node."""
    curDirPath, _ = path.split(node.filePath)
    includedFilePath \
      = type(self)._findFile(node.includedFilePath,
                             self._options.includePaths + [curDirPath])
    if includedFilePath is None:
      message = f'`{node.includedFilePath}` was not found in the include paths'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    try:
      with open(includedFilePath, mode='r') as fp:
        includedFileLines = fp.read().splitlines()
    except IsADirectoryError as error:
      message = f'`{node.includedFilePath}` is a directory, file expected'
      raise TielRuntimeError(message, node.filePath, node.lineNumber) from error
    includedFileTree = TielParser(node.includedFilePath, includedFileLines).parse()
    if node.doPrintLines:
      self.execTree(includedFileTree, printFunc)
    else:
      def _dummyPrintFunc(_): pass
      self.execTree(includedFileTree, _dummyPrintFunc)

  def _execNodeLet(self, node: TielNodeLet) -> None:
    """Execute LET node."""
    if node.name in self._scope:
      message = f'name `{node.name}` is already defined'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    if node.name in _BUILTIN_NAMES:
      message = f'builtin name <{node.name}> can not be redefined'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    if node.arguments is None:
      value = self._evalPyExpr(node.expression,
                               node.filePath, node.lineNumber)
      self._scope[node.name] = value
    else:
      argNames = [arg.strip() for arg in node.arguments.split(',')]
      if len(argNames) > len(set(argNames)):
        message = 'functional <let> arguments must be unique'
        raise TielRuntimeError(message, node.filePath, node.lineNumber)
      # Evaluate functional LET as lambda function.
      expression = f'lambda {node.arguments}: {node.expression}'
      func = self._evalPyExpr(expression,
                              node.filePath, node.lineNumber)
      self._scope[node.name] = func

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

  def _execNodeIfEnd(self, node: TielNodeIfEnd, printFunc: TielPrintFunc) -> None:
    """Execute IF/ELSE IF/ELSE/END IF node."""
    if self._evalPyExpr(node.condition,
                        node.filePath, node.lineNumber):
      self._execNodeList(node.thenNodes, printFunc)
    else:
      for elseIfNode in node.elseIfNodes:
        if self._evalPyExpr(elseIfNode.condition,
                            elseIfNode.filePath, elseIfNode.lineNumber):
          self._execNodeList(elseIfNode.nodes, printFunc)
          break
      else:
        self._execNodeList(node.elseNodes, printFunc)

  def _execNodeDoEnd(self, node: TielNodeDoEnd, printFunc: TielPrintFunc) -> None:
    """Execute DO/END DO node."""
    bounds = self._evalPyExpr(node.bounds,
                              node.filePath, node.lineNumber)
    if not (isinstance(bounds, tuple)
            and (2 <= len(bounds) <= 3)
            and list(map(type, bounds)) == len(bounds) * [int]):
      message = 'tuple of two or three integers inside the <do> ' \
                + f' directive bounds is expected, got `{node.bounds}`'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    start, stop = bounds[0:2]
    step = bounds[2] if len(bounds) == 3 else 1
    # Save and restore previous index value
    # in case we are inside the nested loop.
    prevIndex = self._scope.get('__INDEX__')
    for index in range(start, stop + 1, step):
      self._scope[node.indexName] = index
      self._scope['__INDEX__'] = index
      self._execNodeList(node.nodes, printFunc)
    del self._scope[node.indexName]
    if prevIndex is not None:
      self._scope['__INDEX__'] = prevIndex
    else:
      del self._scope['__INDEX__']

  def _execNodeMacroEnd(self, node: TielNodeMacroEnd) -> None:
    """Execute MACRO/END MACRO node."""
    macroName = node.name.lower()
    if macroName in self._scopeMacros:
      message = f'macro `{node.name}` is already defined'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    # Compile macro patterns.
    type(self)._execNodeListPattern(node.patternNodes)
    # Compile section patterns and check section names.
    if node.construct:
      sectionNames: Set[str] = set()
      for sectionNode in node.sectionNodes:
        sectionName = sectionNode.name.lower()
        if sectionName in sectionNames:
          message = f'macro construct @{node.name} ' \
                    + f'section `{sectionNode.name}` is already defined'
          raise TielRuntimeError(message, node.filePath, node.lineNumber)
        sectionNames.add(sectionName)
        type(self)._execNodeListPattern(sectionNode.patternNodes)
    self._scopeMacros[macroName] = node

  @staticmethod
  def _execNodeListPattern(nodes: List[TielNodePattern]) -> None:
    """Execute PATTERN node list."""
    for node in nodes:
      if isinstance(node.pattern, str):
        try:
          node.pattern = _regExpr(node.pattern)
        except re.error as error:
          message = f'invalid pattern regular expression `{node.pattern}`'
          raise TielRuntimeError(message, node.filePath, node.lineNumber) from error

  def _execNodeCallEnd(self, node: TielNodeCall, printFunc: TielPrintFunc) -> None:
    """Execute CALL/END CALL node."""
    macroName = node.name.lower()
    macroNode = self._scopeMacros[macroName]
    if node.construct != macroNode.construct:
      if macroNode.construct:
        message = f'macro construct `{node.name}` ' \
                  + 'must be called with call construct syntax'
      else:
        message = f'non-construct macro `{node.name}` ' \
                  + 'must be called with call syntax, not call construct'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    # Use a special print function
    # in order to keep indentations from the original source.
    def _spacedPrintFunc(line):
      printFunc(line if line.startswith('#') else node.spaces + line)
    self._matchCallPattern(macroNode, node, _spacedPrintFunc)
    # Match and evaluate macro sections.
    if node.construct:
      self._execNodeList(node.nodes, printFunc)
      for sectionNode in node.sectionNodes:
        sectionName = sectionNode.name.lower()
        macroSectionNode \
          = next((x for x in macroNode.sectionNodes
                  if x.name.lower() == sectionName), None)
        self._matchCallPattern(macroSectionNode,
                               sectionNode, _spacedPrintFunc)
        self._execNodeList(sectionNode.nodes, printFunc)
      self._execNodeList(macroNode.finallyNodes, _spacedPrintFunc)

  def _matchCallPattern(self, macroNode, node, printFunc):
    # Find a match in macro patterns and evaluate primary section.
    for patternNode in macroNode.patternNodes:
      match = patternNode.pattern.match(node.argument)
      if match is not None:
        self._scope = {**self._scope, **match.groupdict()}
        self._execNodeList(patternNode.nodes, printFunc)
        break
    else:
      message = f'macro @{macroNode.name} call does not match any pattern'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)

  def _resolveCall(self,
                   node: TielNodeCallSegment,
                   restNodes: List[TielNode]) -> Tuple[TielNodeCall, List[TielNode]]:
    macroName = node.name.replace(' ', '').lower()
    macroNode = self._scopeMacros.get(macroName)
    if macroNode is None:
      message = f'macro `{node.name}` was not previously defined'
      raise TielRuntimeError(message, node.filePath, node.lineNumber)
    node = TielNodeCall(node)
    node.construct = macroNode.construct
    if node.construct:
      while len(restNodes) != 0:
        nextNode = restNodes.pop(0)
        if isinstance(nextNode, TielNodeCallSegment):
          nodeName = nextNode.name.lower().replace(' ', '')
          # Check if we reached end of call or a call section.
          if nodeName == 'end' + macroName: break
          if nodeName in macroNode.sectionNames():
            nextNode = TielNodeCallSection(nextNode)
            node.sectionNodes.append(nextNode)
            continue
          # Resolve the scoped call.
          nextNode, restNodes = self._resolveCall(nextNode, restNodes)
        # Append the current node to the most recent section of the call node.
        if len(node.sectionNodes) != 0:
          node.sectionNodes[-1].nodes.append(nextNode)
        else:
          node.nodes.append(nextNode)
      else:
        raise RuntimeError('huinya')
    return node, restNodes

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tiel_preprocess(filePath: str,
                    output_filePath: str,
                    options: TielOptions = TielOptions()) -> None:
  """Preprocess the source file."""
  with open(filePath, 'r') as fp:
    lines = fp.read().splitlines()
  tree: TielTree = TielParser(filePath, lines).parse()
  with open(output_filePath, 'w') as fp:
    def _printFunc(line): print(line, file=fp)
    TielExecutor(options).execTree(tree, _printFunc)


def tiel_main() -> None:
  """Fortiel entry point."""
  arg_parser = \
    argparse.ArgumentParser(prog='src')
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
  arg_parser.add_argument('filePath',
                          help='input file path')
  arg_parser.add_argument('output_filePath',
                          help='output file path')
  args = arg_parser.parse_args()
  filePath = args.filePath
  output_filePath = args.output_filePath
  tiel_preprocess(filePath, output_filePath)


if __name__ == '__main__':
  tiel_main()