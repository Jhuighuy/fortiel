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
from typing import Any, Union, \
  List, Dict, Tuple, Callable, Optional, Pattern, Match


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielOptions:
  """Preprocessor options.
  """

  def __init__(self) -> None:
    self.includePaths: List[str] = []


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielError(Exception):
  """Preprocessor syntax tree parse error.
  """
  def __init__(self, message: str, filePath: str, lineNumber: int) -> None:
    super().__init__()
    self.message: str = message
    self.filePath: str = filePath
    self.lineNumber: int = lineNumber

  def __str__(self) -> str:
    message \
      = f'{self.filePath}:{self.lineNumber}:1:\n\nFatal Error: {self.message}'
    return message


class TielSyntaxError(TielError):
  """Unexpected directive preprocessor error.
  """


class TielEvalError(TielError):
  """Error in the directive or line substitution evaluation.
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
  """Unexpected end of file preprocessor error.
  """
  def __init__(self, filePath: str, lineNumber: int):
    super().__init__('unexpected end of file', filePath, lineNumber)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielTree:
  """Preprocessor syntax tree.
  """
  def __init__(self, filePath: str) -> None:
    self.filePath: str = filePath
    self.rootNodes: List[TielNode] = []


class TielNode:
  """Preprocessor syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    self.filePath: str = filePath
    self.lineNumber: int = lineNumber


class TielNodeLineList(TielNode):
  """The list of code lines syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.lines: List[str] = []


class TielNodeImport(TielNode):
  """The IMPORT/INCLUDE directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.includedFilePath: str = ''
    self.doPrintLines: bool = False


class TielNodeLet(TielNode):
  """The LET directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.arguments: Optional[str] = None
    self.expression: str = ''


class TielNodeDel(TielNode):
  """The DEL directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.names: List[str] = []


class TielNodeIfEnd(TielNode):
  """The IF/ELSE IF/ELSE/END IF directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.condition: str = ''
    self.thenNodes: List[TielNode] = []
    self.elseIfNodes: List[TielNodeElseIf] = []
    self.elseNodes: List[TielNode] = []


class TielNodeElseIf(TielNode):
  """The ELSE IF directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.condition: str = ''
    self.nodes: List[TielNode] = []


class TielNodeDoEnd(TielNode):
  """The DO/END DO directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.indexName: str = ''
    self.bounds: str = ''
    self.nodes: List[TielNode] = []


class TielNodeChannelEnd(TielNode):
  """The CHANNEL/END CHANNEL directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.expression: str = ''
    self.nodes: List[TielNode] = []


class TielNodeFlush(TielNode):
  """The FLUSH directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.expression: str = ''


class TielNodeMacroEnd(TielNode):
  """The MACRO/END MACRO directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.isConstruct: bool = False
    self.patterns: List[TielNodePattern] = []


class TielNodePattern(TielNode):
  """The PATTERN directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.pattern: Union[str, Pattern[str]] = ''
    self.nodes: List[TielNode] = []


class TielNodeCallEnd(TielNode):
  """The CALL/END CALL directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.isConstruct: bool = False
    self.argument: str = ''
    self.nodes: List[TielNode] = []
    self.sectionNodes: List[TielNodeSection] = []


class TielNodeSection(TielNode):
  """The CALL SECTION directive syntax tree node."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.argument: str = ''
    self.nodes: List[TielNode] = []


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def _regExpr(pattern: str) -> Pattern[str]:
  return re.compile(pattern, re.IGNORECASE)


_DIR = _regExpr(r'^\s*#@\s*(?P<dir>.*)?$')
_DIR_HEAD = _regExpr(r'^(?P<word>[^\s]+)(?:\s+(?P<word2>[^\s]+))?')

_IMPORT = _regExpr(r'^(?P<dir>import|include)\s+'
                   + r'(?P<path>(?:\".+\")|(?:\'.+\')|(?:\<.+\>))$')

_LET = _regExpr(r'^let\s+(?P<name>[a-zA-Z_]\w*)\s*'
                + r'(?P<args>\((?:\*?\*?[a-zA-Z]\w*(?:\s*,\s*\*?\*?[a-zA-Z]\w*)*)?\s*\))?\s*'
                + r'=\s*(?P<expr>.*)$')

_DEL = _regExpr(r'^undef\s+(?P<names>[a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)*)$')

_IF = _regExpr(r'^if\s*(?P<cond>.+)\s*:?$')
_ELSE_IF = _regExpr(r'^else\s*if\s*(?P<cond>.+)\s*:?$')
_ELSE = _regExpr(r'^else$')
_END_IF = _regExpr(r'^end\s*if$')

_DO = _regExpr(r'^do\s+(?P<index>[a-zA-Z_]\w*)\s*=\s*(?P<bounds>.*)\s*:?$')
_END_DO = _regExpr(r'^end\s*do$')

_CHANNEL = _regExpr(r'^channel(?:\s+(?P<expression>.+))?$')
_END_CHANNEL = _regExpr(r'^end\s*channel$')
_FLUSH = _regExpr(r'^flush(?:\s+(?P<expression>.+))?$')

_MACRO = _regExpr(r'^macro\s+(?P<construct>construct\s+)?'
                  + r'(?P<name>[a-zA-Z]\w*)(?:\s+(?P<pattern>.*))?$')
_PATTERN = _regExpr(r'^pattern\s+(?P<pattern>.*)$')
_END_MACRO = _regExpr(r'^end\s*macro(?:\s+(?P<name>[a-zA-Z]\w*))?$')

_CALL = _regExpr(r'^call\s+(?P<construct>construct\s+)?'
                 + r'(?P<name>[a-zA-Z]\w*)\s+(?P<argument>.*)$')
_SECTION = _regExpr(r'^section\s+(?P<name>[a-zA-Z]\w*)\s+(?P<argument>.*)$')
_END_CALL = _regExpr(r'^end\s*call(?:\s+(?P<name>[a-zA-Z]\w*))?$')

_LINE = _regExpr(r'(line)?\s*(?P<num>\d+)\s+(?P<path>(\'.+\')|(\".+\"))')


class TielParser:
  """Preprocessor syntax tree parser.
  """
  def __init__(self,
               filePath: str, lines: List[str]) -> None:
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
    self._currentLine: str = \
      '' if self._matchesEnd() else self._lines[self._currentLineIndex].rstrip()

  def _matchesLine(self, *patterns: Pattern[str]) -> Optional[Match[str]]:
    if self._matchesEnd():
      raise TielEndError(self._filePath, self._currentLineNumber)
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
        raise TielEndError(self._filePath, self._currentLineNumber)
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
      tree.rootNodes.append(self._parseSingle())
    return tree

  def _parseSingle(self) -> TielNode:
    """Parse a directive or a line list."""
    if self._matchesLine(_DIR):
      return self._parseDirective()
    return self._parseLineList()

  def _parseLineList(self) -> TielNodeLineList:
    """Parse a line list."""
    node = TielNodeLineList(self._filePath,
                            self._currentLineNumber)
    while True:
      node.lines.append(self._currentLine)
      self._advanceLine()
      if self._matchesEnd() or self._matchesLine(_DIR):
        break
    return node

  def _parseDirective(self) -> TielNode:
    """Parse a directive."""
    self._parseLineContinuation()
    directive = self._matchesLine(_DIR)['dir']
    dirHead = type(self)._parseHead(directive)
    if dirHead in ['import', 'include']:
      return self._parseDirectiveImport()
    if dirHead == 'let':
      return self._parseDirectiveLet()
    if dirHead == 'del':
      return self._parseDirectiveDel()
    if dirHead == 'if':
      return self._parseDirectiveIfEnd()
    if dirHead == 'do':
      return self._parseDirectiveDoEnd()
    if dirHead == 'channel':
      return self._parseDirectiveChannelEnd()
    if dirHead == 'flush':
      return self._parseDirectiveFlush()
    if dirHead == 'macro':
      return self._parseDirectiveMacroEnd()
    if dirHead == 'call':
      return self._parseDirectiveCallEnd()
    if dirHead == 'line' or (dirHead is not None and dirHead.isdecimal()):
      self._evalDirectiveLine()
      return self._parseSingle()
    # Determine the error type:
    # either the known directive is misplaced,
    # either the directive is unknown.
    if dirHead is None:
      message = f'empty directive'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    elif dirHead in ['else', 'else if', 'end'+'if', 'end'+'do',
                     'end'+'channel', 'pattern', 'end'+'macro', 'section', 'end'+'call']:
      message = f'misplaced directive <{dirHead}>'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    else:
      message = f'unknown or mistyped directive <{dirHead}>'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)

  def _matchesDirectiveHead(self, *dirHeadList: str) -> Optional[str]:
    if self._matchesLine(_DIR) is not None:
      # Parse continuations and rematch.
      self._parseLineContinuation()
      dirMatch = self._matchesLine(_DIR)
      directive = dirMatch['dir'].lower()
      dirHead = type(self)._parseHead(directive)
      if dirHead in [head.replace(' ', '') for head in dirHeadList]:
        return dirHead
    return None

  def _matchDirectiveSyntax(self, pattern: Pattern[str],
                            *groupLists: str) -> Union[str, Tuple[str, ...]]:
    directive = self._matchesLine(_DIR).group('dir').rstrip()
    match = pattern.match(directive)
    if match is None:
      dirHead = type(self)._parseHead(directive)
      message = f'invalid <{dirHead}> directive syntax'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    self._advanceLine()
    return match.group(*groupLists)

  def _parseDirectiveImport(self) -> TielNodeImport:
    """Parse IMPORT/INCLUDE directives."""
    node = TielNodeImport(self._filePath,
                          self._currentLineNumber)
    dirHead, node.includedFilePath \
      = self._matchDirectiveSyntax(_IMPORT, 'dir', 'path')
    node.includedFilePath = node.includedFilePath[1:-1]
    if dirHead.lower() == 'include':
      node.doPrintLines = True
    return node

  def _parseDirectiveLet(self) -> TielNodeLet:
    """Parse LET directive."""
    # Note that we are not
    # evaluating or validating define arguments and body here.
    node = TielNodeLet(self._filePath,
                       self._currentLineNumber)
    node.name, node.arguments, node.expression \
      = self._matchDirectiveSyntax(_LET, 'name', 'args', 'expr')
    if node.arguments is not None:
      node.arguments = node.arguments[1:-1].strip()
    return node

  def _parseDirectiveDel(self) -> TielNodeDel:
    """Parse DEL directive."""
    # Note that we are not
    # evaluating or validating define name here.
    node = TielNodeDel(self._filePath,
                       self._currentLineNumber)
    names = self._matchDirectiveSyntax(_DEL, 'names')
    node.names = [name.strip() for name in names.split(',')]
    return node

  def _parseDirectiveIfEnd(self) -> TielNodeIfEnd:
    """Parse IF/ELSE IF/ELSE/END IF directives."""
    # Note that we are not evaluating
    # or validating condition expressions here.
    node = TielNodeIfEnd(self._filePath,
                         self._currentLineNumber)
    node.condition = self._matchDirectiveSyntax(_IF, 'cond')
    while not self._matchesDirectiveHead('else if', 'else', 'end if'):
      node.thenNodes.append(self._parseSingle())
    if self._matchesDirectiveHead('else if'):
      while not self._matchesDirectiveHead('else', 'end if'):
        elseIfNode = TielNodeElseIf(self._filePath,
                                    self._currentLineNumber)
        elseIfNode.condition = self._matchDirectiveSyntax(_ELSE_IF, 'cond')
        while not self._matchesDirectiveHead('else if', 'else', 'end if'):
          elseIfNode.nodes.append(self._parseSingle())
        node.elseIfNodes.append(elseIfNode)
    if self._matchesDirectiveHead('else'):
      self._matchDirectiveSyntax(_ELSE)
      while not self._matchesDirectiveHead('end if'):
        node.elseNodes.append(self._parseSingle())
    self._matchDirectiveSyntax(_END_IF)
    return node

  def _parseDirectiveDoEnd(self) -> TielNodeDoEnd:
    """Parse DO/END DO directives."""
    # Note that we are not evaluating
    # or validating loop bound expressions here.
    node = TielNodeDoEnd(self._filePath,
                         self._currentLineNumber)
    node.indexName, node.bounds \
      = self._matchDirectiveSyntax(_DO, 'index', 'bounds')
    while not self._matchesDirectiveHead('end do'):
      node.nodes.append(self._parseSingle())
    self._matchDirectiveSyntax(_END_DO)
    return node

  def _parseDirectiveChannelEnd(self) -> TielNodeChannelEnd:
    """Parse CHANNEL/END CHANNEL directives."""
    node = TielNodeChannelEnd(self._filePath,
                              self._currentLineNumber)
    node.expression \
      = self._matchDirectiveSyntax(_CHANNEL, 'expression')
    while not self._matchesDirectiveHead('end channel'):
      node.nodes.append(self._parseSingle())
    self._matchDirectiveSyntax(_END_CHANNEL)
    return node

  def _parseDirectiveFlush(self) -> TielNodeFlush:
    """Parse FLUSH directives."""
    node = TielNodeFlush(self._filePath,
                         self._currentLineNumber)
    node.expression \
      = self._matchDirectiveSyntax(_FLUSH, 'expression')
    return node

  def _parseDirectiveMacroEnd(self) -> TielNodeMacroEnd:
    """Parse MACRO/END MACRO directives."""
    node = TielNodeMacroEnd(self._filePath,
                            self._currentLineNumber)
    node.name, node.isConstruct, pattern \
      = self._matchDirectiveSyntax(_MACRO, 'name', 'construct', 'pattern')
    node.name = node.name.lower()
    node.isConstruct = node.isConstruct is not None
    if pattern is not None:
      patternNode = TielNodePattern(node.filePath,
                                    node.lineNumber)
      patternNode.pattern = pattern
      while not self._matchesDirectiveHead('pattern', 'end macro'):
        patternNode.nodes.append(self._parseSingle())
      node.patterns.append(patternNode)
    elif not self._matchesDirectiveHead('pattern'):
      message = 'expected <pattern> directive'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    if self._matchesDirectiveHead('pattern'):
      while not self._matchesDirectiveHead('end macro'):
        patternNode = TielNodePattern(self._filePath,
                                      self._currentLineNumber)
        patternNode.pattern = \
          self._matchDirectiveSyntax(_PATTERN, 'pattern')
        while not self._matchesDirectiveHead('pattern', 'end macro'):
          patternNode.nodes.append(self._parseSingle())
        node.patterns.append(patternNode)
    endName = self._matchDirectiveSyntax(_END_MACRO, 'name')
    if endName is not None and node.name != endName.lower():
      message = f'<end macro> expected `{node.name}`, got `{endName}`'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    return node

  def _parseDirectiveCallEnd(self) -> TielNodeCallEnd:
    """Parse CALL/END CALL directives."""
    # Note that we are not evaluating
    # or matching call arguments and sections here.
    node = TielNodeCallEnd(self._filePath,
                           self._currentLineNumber)
    node.name, node.isConstruct, node.argument \
      = self._matchDirectiveSyntax(_CALL, 'name', 'construct', 'argument')
    node.name = node.name.lower()
    node.isConstruct = node.isConstruct is not None
    if node.isConstruct:
      while not self._matchesDirectiveHead('section', 'end call'):
        node.nodes.append(self._parseSingle())
      if self._matchesDirectiveHead('section'):
        while not self._matchesDirectiveHead('end call'):
          sectionNode = TielNodeSection(self._filePath,
                                        self._currentLineNumber)
          sectionNode.name, sectionNode.argument \
            = self._matchDirectiveSyntax(_SECTION, 'name', 'argument')
          while not self._matchesDirectiveHead('section', 'end call'):
            sectionNode.nodes.append(self._parseSingle())
          node.sectionNodes.append(sectionNode)
      endName = self._matchDirectiveSyntax(_END_CALL, 'name')
      if endName is not None and node.name != endName.lower():
        message = f'<end call> expected `{node.name}`, got `{endName}`'
        raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    return node

  def _evalDirectiveLine(self) -> None:
    """Evaluate LINE directive."""
    self._filePath, self._currentLineNumber \
      = self._matchDirectiveSyntax(_LINE, 'path', 'num')
    self._filePath = self._filePath[1:-1]
    self._currentLineNumber = int(self._currentLineNumber)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_BUILTIN_NAMES = [
  '__FILE__', '__LINE__',
  '__DATE__', '__TIME__',
  '__INDEX__',
]


TielPrintFunc = Callable[[str], None]


class TielEvaluator:
  """Preprocessor syntax tree evaluator.
  """
  def __init__(self, options: TielOptions):
    self._scope: Dict[str, Any] = {}
    self._scopeMacros: Dict[str, TielNodeMacroEnd] = {}
    self._channel: str = ''
    self._channeledLines: Dict[str, List[str]] = {}
    self._options: TielOptions = options

  def evalTree(self, tree: TielTree, printFunc: TielPrintFunc) -> None:
    """Evaluate the syntax tree or the syntax tree node."""
    self._evalNodeList(tree.rootNodes, printFunc)

  def _evalNodeList(self, nodes: List[TielNode], printFunc: TielPrintFunc) -> None:
    """Evaluate the syntax tree node or a list of nodes."""
    for node in nodes:
      if isinstance(node, TielNodeLineList):
        self._evalLineList(node, printFunc)
      else:
        self._evalDirective(node, printFunc)

  def _evalPyExpr(self,
                  expression: str, filePath: str, lineNumber: int) -> Any:
    """Evaluate Python expression."""
    try:
      value = eval(expression, self._scope)
      return value
    except Exception as error:
      message = 'Python expression evaluation error: ' \
                + f'{str(error).replace("<string>", f"expression `{expression}`")}'
      raise TielEvalError(message, filePath, lineNumber) from error

  def _evalLine(self, line: str, filePath: str, lineNumber: int,
                printFunc: TielPrintFunc) -> None:
    """Evaluate in-line substitutions."""
    # Skip comment lines (no inline comments for now).
    if line.lstrip().startswith('!'):
      printFunc(line)
      return
    # Evaluate expression substitutions.
    def _lineSub(match: Match[str]) -> str:
      expression = match['expr']
      return str(self._evalPyExpr(expression, filePath, lineNumber))
    line = re.sub(r'`(?P<expr>[^`]+)`', _lineSub, line)
    # Evaluate <@:> substitutions.
    def _loopSub(match: Match[str]) -> str:
      expression = match['expr']
      index = self._scope.get('__INDEX__')
      if index is None:
        message = '<@:> substitution outside of the <do> loop body'
        raise TielEvalError(message, filePath, lineNumber)
      return str(index * expression)
    line = re.sub(r'@(?P<expr>:(\s*,)?)', _loopSub, line)
    printFunc(line)

  def _evalLineList(self, node: TielNodeLineList, printFunc: TielPrintFunc) -> None:
    """Evaluate line block."""
    printFunc(f'# {node.lineNumber} "{node.filePath}"')
    for lineNumber, line in \
        enumerate(node.lines, start=node.lineNumber):
      self._evalLine(line, node.filePath, lineNumber, printFunc)

  def _evalDirective(self, node: TielNode, printFunc: TielPrintFunc):
    """Evaluate directive."""
    if isinstance(node, TielNodeImport):
      return self._evalDirectiveImport(node, printFunc)
    if isinstance(node, TielNodeLet):
      return self._evalDirectiveLet(node)
    if isinstance(node, TielNodeDel):
      return self._evalDirectiveDel(node)
    if isinstance(node, TielNodeIfEnd):
      return self._evalDirectiveIfEnd(node, printFunc)
    if isinstance(node, TielNodeDoEnd):
      return self._evalDirectiveDoEnd(node, printFunc)
    if isinstance(node, TielNodeChannelEnd):
      return self._evalDirectiveChannelEnd(node, printFunc)
    if isinstance(node, TielNodeFlush):
      return self._evalDirectiveFlush(node, printFunc)
    if isinstance(node, TielNodeMacroEnd):
      return self._evalDirectiveMacroEnd(node)
    if isinstance(node, TielNodeCallEnd):
      return self._evalDirectiveCallEnd(node, printFunc)
    nodeType = type(node).__name__
    raise RuntimeError(f'no evaluator for directive type {nodeType}')

  @staticmethod
  def _findFile(filePath: str, dirPaths: List[str]) -> Optional[str]:
    filePath = path.expanduser(filePath)
    if path.exists(filePath):
      return filePath
    for dirPath in dirPaths:
      filePathInDir = path.expanduser(path.join(dirPath, filePath))
      if path.exists(filePathInDir):
        return filePathInDir
    return None

  def _evalDirectiveImport(self, node: TielNodeImport, printFunc: TielPrintFunc) -> None:
    """Evaluate IMPORT/INCLUDE directive."""
    curDirPath, _ = path.split(node.filePath)
    includedFilePath \
      = type(self)._findFile(node.includedFilePath,
                             self._options.includePaths + [curDirPath])
    if includedFilePath is None:
      message = f'`{node.includedFilePath}` was not found in the include paths'
      raise TielFileError(message, node.filePath, node.lineNumber)
    try:
      with open(includedFilePath, mode='r') as fp:
        includedFileLines = fp.read().splitlines()
    except IsADirectoryError as error:
      message = f'`{node.includedFilePath}` is a directory, file expected'
      raise TielFileError(message, node.filePath, node.lineNumber) from error
    includedFileTree = TielParser(node.includedFilePath, includedFileLines).parse()
    if node.doPrintLines:
      self.evalTree(includedFileTree, printFunc)
    else:
      def _dummyPrintFunc(_): pass
      self.evalTree(includedFileTree, _dummyPrintFunc)

  def _evalDirectiveLet(self, node: TielNodeLet) -> None:
    """Evaluate LET directive."""
    if node.name in self._scope:
      message = f'name `{node.name}` is already defined'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    if node.name in _BUILTIN_NAMES:
      message = f'builtin name <{node.name}> can not be redefined'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    if node.arguments is None:
      value = self._evalPyExpr(node.expression,
                               node.filePath, node.lineNumber)
      self._scope[node.name] = value
    else:
      argNames = [arg.strip() for arg in node.arguments.split(',')]
      if len(argNames) > len(set(argNames)):
        message = 'functional <let> arguments must be unique'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      # Evaluate functional LET as lambda function.
      expression = f'lambda {node.arguments}: {node.expression}'
      func = self._evalPyExpr(expression,
                              node.filePath, node.lineNumber)
      self._scope[node.name] = func

  def _evalDirectiveDel(self, node: TielNodeDel) -> None:
    """Evaluate DEL directive."""
    for name in node.names:
      if name not in self._scope:
        message = f'name `{name}` was not previously defined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      if name in _BUILTIN_NAMES:
        message = f'builtin name <{name}> can not be undefined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      del self._scope[name]

  def _evalDirectiveIfEnd(self, node: TielNodeIfEnd, printFunc: TielPrintFunc) -> None:
    """Evaluate IF/ELSE IF/ELSE/END IF node."""
    if self._evalPyExpr(node.condition,
                        node.filePath, node.lineNumber):
      self._evalNodeList(node.thenNodes, printFunc)
    else:
      for elseIfNode in node.elseIfNodes:
        if self._evalPyExpr(elseIfNode.condition,
                            elseIfNode.filePath, elseIfNode.lineNumber):
          self._evalNodeList(elseIfNode.nodes, printFunc)
          break
      else:
        self._evalNodeList(node.elseNodes, printFunc)

  def _evalDirectiveDoEnd(self, node: TielNodeDoEnd, printFunc: TielPrintFunc) -> None:
    """Evaluate DO/END DO node."""
    bounds = self._evalPyExpr(node.bounds,
                              node.filePath, node.lineNumber)
    if not (isinstance(bounds, tuple)
            and (2 <= len(bounds) <= 3)
            and list(map(type, bounds)) == len(bounds) * [int]):
      message = 'tuple of two or three integers inside the <do> ' \
                + f' directive bounds is expected, got `{node.bounds}`'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    start, stop = bounds[0:2]
    step = bounds[2] if len(bounds) == 3 else 1
    # Save and restore previous index value
    # in case we are inside the nested loop.
    prevIndex = self._scope.get('__INDEX__')
    for index in range(start, stop + 1, step):
      self._scope[node.indexName] = index
      self._scope['__INDEX__'] = index
      self._evalNodeList(node.nodes, printFunc)
    del self._scope[node.indexName]
    if prevIndex is not None:
      self._scope['__INDEX__'] = prevIndex
    else:
      del self._scope['__INDEX__']

  def _evalDirectiveChannelEnd(self, node: TielNodeChannelEnd, printFunc: TielPrintFunc) -> None:
    """Evaluate CHANNEL/END CHANNEL node."""
    channel = self._evalPyExpr(node.expression,
                               node.filePath, node.lineNumber)
    if not isinstance(channel, str):
      message = f'channel name must to be a string'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    if channel == '':
      self._evalNodeList(node.nodes, printFunc)
    else:
      channelLines: List[str] = []
      def _printToChannelFunc(line): channelLines.append(line)
      self._evalNodeList(node.nodes, _printToChannelFunc)
      if channel in self._channeledLines:
        self._channeledLines[channel] = channelLines
      else:
        self._channeledLines[channel] += channelLines

  def _evalDirectiveFlush(self, node: TielNodeFlush, printFunc: TielPrintFunc) -> None:
    """Evaluate FLUSH node."""
    channels = self._evalPyExpr(node.expression,
                                node.filePath, node.lineNumber)
    if not isinstance(channels, tuple):
      channels = (channels,)
    for channel in channels:
      if not isinstance(channel, str):
        message = f'channel name must to be a string'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      channelLines = self._channeledLines.get(channel)
      if channelLines is not None:
        for line in channelLines:
          printFunc(line)
        del self._channeledLines[channel]

  def _evalDirectiveMacroEnd(self, node: TielNodeMacroEnd) -> None:
    """Evaluate MACRO/END MACRO node."""
    if node.name in self._scopeMacros:
      message = f'macro `{node.name}` is already defined'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    for patternNode in node.patterns:
      if isinstance(patternNode.pattern, str):
        try:
          patternNode.pattern = _regExpr(patternNode.pattern)
        except re.error as error:
          message = f'invalid macro @{node.name} pattern `{patternNode.pattern}`'
          raise TielEvalError(message, patternNode.filePath, patternNode.lineNumber) from error
    self._scopeMacros[node.name] = node

  def _evalDirectiveCallEnd(self, node: TielNodeCallEnd, printFunc: TielPrintFunc) -> None:
    """Evaluate CALL/END CALL node."""
    macroNode = self._scopeMacros.get(node.name)
    if macroNode is None:
      message = f'macro `{node.name}` was not previously defined'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    # Find a match in macro patterns.
    for patternNode in macroNode.patterns:
      match = patternNode.pattern.match(node.argument)
      if match is not None:
        self._scope = {**self._scope, **match.groupdict()}
        self._evalNodeList(patternNode.nodes, printFunc)
        break
    else:
      message = f'macro @{macroNode.name} call does not match any pattern'
      raise TielEvalError(message, node.filePath, node.lineNumber)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tiel_preprocess(filePath: str,
                    output_filePath: str,
                    options: TielOptions = TielOptions()) -> None:
  """Preprocess the source file."""
  with open(filePath, 'r') as fp:
    lines = fp.read().splitlines()
  tree = TielParser(filePath, lines).parse()
  with open(output_filePath, 'w') as fp:
    def _printFunc(line): print(line, file=fp)
    TielEvaluator(options).evalTree(tree, _printFunc)


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
