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
  List, Set, Dict, Tuple, Callable, Optional, Pattern, Match, cast


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
    self.mutators: List[Tuple[Pattern[str], str]] = []


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
    self.patternNodes: List[TielNodePattern] = []
    self.sectionNodes: List[TielNodeSection] = []
    self.finallyNodes: List[TielNode] = []


class TielNodeSection(TielNode):
  """The SECTION directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.isOnce: bool = False
    self.patternNodes: List[TielNodePattern] = []


class TielNodePattern(TielNode):
  """The PATTERN directive syntax tree node.
  """
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.pattern: Union[str, Pattern[str]] = ''
    self.nodes: List[TielNode] = []


class TielNodeCallSegment(TielNode):
  """The CALL SEGMENT directive."""
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.argument: str = ''


class TielNodeCall(TielNode):
  """The CALL/END CALL directive syntax tree node."""
  def __init__(self, segment: TielNodeCallSegment) -> None:
    super().__init__(segment.filePath, segment.lineNumber)
    self.name: str = segment.name
    self.argument: str = segment.argument
    self.isConstruct: bool = False
    self.nodes: List[TielNode] = []
    self.sectionNodes: List[TielNodeCallSection] = []


class TielNodeCallSection(TielNode):
  """The CALL SECTION directive syntax tree node."""
  def __init__(self, segment: TielNodeCallSegment) -> None:
    super().__init__(segment.filePath, segment.lineNumber)
    self.name: str = ''
    self.argument: str = ''
    self.nodes: List[TielNode] = []


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def _regExpr(pattern: str) -> Pattern[str]:
  return re.compile(pattern, re.IGNORECASE)


_DIRECTIVE = _regExpr(r'^\s*(?P<directive>[^!]*)(!.*)?$')
_DIR_HEAD = _regExpr(r'^(?P<word>[^\s]+)(?:\s+(?P<word2>[^\s]+))?')

_USE = _regExpr(r'^(?P<head>import|include)\s+'
                + r'(?P<path>(?:\".+\")|(?:\'.+\')|(?:\<.+\>))$')

_LET = _regExpr(r'^let\s+(?P<name>[_a-zA-Z]\w*)\s*'
                + r'(?P<arguments>\((?:\*{0,2}[_a-zA-Z]\w*'
                + r'(?:\s*,\s*\*{0,2}[_a-zA-Z]\w*)*)?\s*\))?\s*'
                + r'=\s*(?P<expression>.*)$')

_DEL = _regExpr(r'^del\s+(?P<names>[a-zA-Z_]\w*(?:\s*,\s*[a-zA-Z_]\w*)*)$')

_IF = _regExpr(r'^if\s*\((?P<condition>.+)\)\s*then$')
_ELSE_IF = _regExpr(r'^else\s*if\s*\((?P<condition>.+)\)\s*then$')
_ELSE = _regExpr(r'^else$')
_END_IF = _regExpr(r'^end\s*if$')

_DO = _regExpr(r'^do\s+(?P<index>[a-zA-Z_]\w*)\s*=\s*(?P<bounds>.*)\s*:?$')
_END_DO = _regExpr(r'^end\s*do$')

_MISPLACED_HEADS = ['else', 'else if', 'end if', 'end do', 'end channel',
                    'section', 'finally', 'pattern', 'end macro', 'end call']


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
    if self._matchesEnd():
      self._currentLine = ''
    else:
      self._currentLine = self._lines[self._currentLineIndex].rstrip()

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

  @staticmethod
  def _inHeadList(head: Optional[str], headList) -> bool:
    headList = [head.replace(' ', '') for head in headList]
    return head is not None and head.replace(' ', '') in headList

  def parse(self) -> TielTree:
    """Parse the source lines."""
    tree = TielTree(self._filePath)
    while not self._matchesEnd():
      tree.rootNodes.append(self._parseSingle())
    return tree

  def _parseSingle(self) -> TielNode:
    """Parse a directive or a line list."""
    if self._matchesLine(_DIRECTIVE):
      return self._parseProcedureStatement()
    return self._parseLineList()

  def _parseProcedureStatement(self) -> TielNode:
    """Parse a procedure statement."""
    self._parseLineContinuation()
    directive = self._matchesLine(_DIRECTIVE)['directive']
    dirHead = type(self)._parseHead(directive)
    if dirHead in ['import', 'include']:
      return self._parseDirectiveImport()
    if dirHead == 'if':
      return self._parseStatementIfEnd()
    if dirHead == 'do':
      return self._parseStatementDoEnd()
    return self._parseLineList()

  def _parseLineList(self) -> TielNodeLineList:
    """Parse a line list."""
    node = TielNodeLineList(self._filePath,
                            self._currentLineNumber)
    node.lines.append(self._currentLine)
    self._advanceLine()
    return node

  def _matchesHead(self, *dirHeadList: str) -> Optional[str]:
    if self._matchesLine(_DIRECTIVE) is not None:
      # Parse continuations and rematch.
      self._parseLineContinuation()
      dirMatch = self._matchesLine(_DIRECTIVE)
      directive = dirMatch['directive'].lower()
      dirHead = type(self)._parseHead(directive)
      if type(self)._inHeadList(dirHead, dirHeadList):
        return dirHead
    return None

  def _matchSyntax(self,
                   pattern: Pattern[str],
                   *groups: str) -> Union[str, Tuple[str, ...]]:
    directive = self._matchesLine(_DIRECTIVE).group('directive').rstrip()
    match = pattern.match(directive)
    if match is None:
      dirHead = type(self)._parseHead(directive)
      message = f'invalid <{dirHead}> directive syntax'
      raise TielSyntaxError(message, self._filePath, self._currentLineNumber)
    self._advanceLine()
    return match.group(*groups)

  def _parseDirectiveImport(self) -> TielNodeImport:
    """Parse IMPORT/INCLUDE directives."""
    node = TielNodeImport(self._filePath,
                          self._currentLineNumber)
    dirHead, node.includedFilePath \
      = self._matchSyntax(_USE, 'head', 'path')
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
      = self._matchSyntax(_LET, 'name', 'arguments', 'expression')
    if node.arguments is not None:
      node.arguments = node.arguments[1:-1].strip()
    return node

  def _parseDirectiveDel(self) -> TielNodeDel:
    """Parse DEL directive."""
    # Note that we are not
    # evaluating or validating define name here.
    node = TielNodeDel(self._filePath,
                       self._currentLineNumber)
    names = self._matchSyntax(_DEL, 'names')
    node.names = [name.strip() for name in names.split(',')]
    return node

  def _parseStatementIfEnd(self) -> TielNodeIfEnd:
    """Parse IF/ELSE IF/ELSE/END IF statement."""
    # Note that we are not evaluating
    # or validating condition expressions here.
    node = TielNodeIfEnd(self._filePath,
                         self._currentLineNumber)
    node.condition \
      = self._matchSyntax(_IF, 'condition')
    while not self._matchesHead('else if', 'else', 'end if'):
      node.thenNodes.append(self._parseSingle())
    if self._matchesHead('else if'):
      while not self._matchesHead('else', 'end if'):
        elseIfNode = TielNodeElseIf(self._filePath,
                                    self._currentLineNumber)
        elseIfNode.condition \
          = self._matchSyntax(_ELSE_IF, 'condition')
        while not self._matchesHead('else if', 'else', 'end if'):
          elseIfNode.nodes.append(self._parseSingle())
        node.elseIfNodes.append(elseIfNode)
    if self._matchesHead('else'):
      self._matchSyntax(_ELSE)
      while not self._matchesHead('end if'):
        node.elseNodes.append(self._parseSingle())
    self._matchSyntax(_END_IF)
    return node

  def _parseStatementDoEnd(self) -> TielNodeDoEnd:
    """Parse DO/END DO statement."""
    # Note that we are not evaluating
    # or validating loop bound expressions here.
    node = TielNodeDoEnd(self._filePath,
                         self._currentLineNumber)
    node.indexName, node.bounds \
      = self._matchSyntax(_DO, 'index', 'bounds')
    while not self._matchesHead('end do'):
      node.nodes.append(self._parseSingle())
    self._matchSyntax(_END_DO)
    return node


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
    for node in _resolveCall(nodes, self._scopeMacros):
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
                + f'{str(error).replace("<head>", f"expression `{expression}`")}'
      raise TielEvalError(message, filePath, lineNumber) from error

  def _evalLine(self, line: str, filePath: str, lineNumber: int,
                printFunc: TielPrintFunc) -> None:
    """Evaluate in-line substitutions."""
    # Skip comment lines (no inline comments for now).
    # TODO: add comments support.
    if line.lstrip().startswith('!'):
      printFunc(line)
      return
    # Evaluate name substitutions.
    def _nameSub(match: Match[str]) -> str:
      name = match['name']
      value = self._scope.get(name)
      if value is None:
        message = f'variable ${name} was not previously declared'
        raise TielEvalError(message, filePath, lineNumber)
      return str(value)
    line = re.sub(r'\$\s*(?P<name>[_a-zA-Z]\w*)\b', _nameSub, line)
    # Evaluate expression substitutions.
    def _lineSub(match: Match[str]) -> str:
      expression = match['expr']
      return str(self._evalPyExpr(expression, filePath, lineNumber))
    line = re.sub(r'`(?P<expr>[^`]+)`', _lineSub, line)
    # Evaluate <@:> substitutions.
    def _loopSub(match: Match[str]) -> str:
      expression = match['expression']
      index = self._scope.get('__INDEX__')
      if index is None:
        message = '<@:> substitution outside of the <do> loop body'
        raise TielEvalError(message, filePath, lineNumber)
      return str(index * expression)
    line = re.sub(r'@(?P<expression>:(\s*,)?)', _loopSub, line)
    printFunc(line)

  def _evalLineList(self,
                    node: TielNodeLineList,
                    printFunc: TielPrintFunc) -> None:
    """Evaluate line block."""
    printFunc(f'# {node.lineNumber} "{node.filePath}"')
    for lineNumber, line in \
        enumerate(node.lines, start=node.lineNumber):
      self._evalLine(line, node.filePath, lineNumber, printFunc)

  def _evalDirective(self,
                     node: TielNode,
                     printFunc: TielPrintFunc):
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
    if isinstance(node, TielNodeCall):
      return self._evalDirectiveCallEnd(node, printFunc)
    if isinstance(node, TielNodeCallSegment):
      raise RuntimeError('internal error: unresolved call segment')
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
    return None

  def _evalDirectiveImport(self,
                           node: TielNodeImport,
                           printFunc: TielPrintFunc) -> None:
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

  def _evalDirectiveLet(self,
                        node: TielNodeLet) -> None:
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

  def _evalDirectiveDel(self,
                        node: TielNodeDel) -> None:
    """Evaluate DEL directive."""
    for name in node.names:
      if name not in self._scope:
        message = f'name `{name}` was not previously defined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      if name in _BUILTIN_NAMES:
        message = f'builtin name <{name}> can not be undefined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      del self._scope[name]

  def _evalDirectiveIfEnd(self,
                          node: TielNodeIfEnd,
                          printFunc: TielPrintFunc) -> None:
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

  def _evalDirectiveDoEnd(self,
                          node: TielNodeDoEnd,
                          printFunc: TielPrintFunc) -> None:
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

  def _evalDirectiveChannelEnd(self,
                               node: TielNodeChannelEnd,
                               printFunc: TielPrintFunc) -> None:
    """Evaluate CHANNEL/END CHANNEL node."""
    channel = self._evalPyExpr(node.expression,
                               node.filePath, node.lineNumber)
    if not isinstance(channel, str):
      message = 'channel name must to be a head'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    if channel == '':
      self._evalNodeList(node.nodes, printFunc)
    else:
      channelLines: List[str] = []
      def _printToChannelFunc(line): channelLines.append(line)
      self._evalNodeList(node.nodes, _printToChannelFunc)
      if channel in self._channeledLines:
        self._channeledLines[channel] += channelLines
      else:
        self._channeledLines[channel] = channelLines

  def _evalDirectiveFlush(self, node: TielNodeFlush, printFunc: TielPrintFunc) -> None:
    """Evaluate FLUSH node."""
    channels = self._evalPyExpr(node.expression,
                                node.filePath, node.lineNumber)
    if not isinstance(channels, tuple):
      channels = (channels,)
    for channel in channels:
      if not isinstance(channel, str):
        message = f'channel name must to be a head'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      channelLines = self._channeledLines.get(channel)
      if channelLines is not None:
        for line in channelLines:
          printFunc(line)
        del self._channeledLines[channel]

  def _evalDirectiveMacroEnd(self,
                             node: TielNodeMacroEnd) -> None:
    """Evaluate MACRO/END MACRO node."""
    macroName = node.name.lower()
    if macroName in self._scopeMacros:
      message = f'macro `{node.name}` is already defined'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    # Compile macro patterns.
    type(self)._evalDirectivePatternList(node.patternNodes)
    # Compile section patterns and check section names.
    if node.isConstruct:
      sectionNames: Set[str] = set()
      for sectionNode in node.sectionNodes:
        sectionName = sectionNode.name.lower()
        if sectionName in sectionNames:
          message = f'macro construct @{node.name} ' \
                    + f'section `{sectionNode.name}` is already defined'
          raise TielEvalError(message, node.filePath, node.lineNumber)
        sectionNames.add(sectionName)
        type(self)._evalDirectivePatternList(sectionNode.patternNodes)
    self._scopeMacros[macroName] = node

  @staticmethod
  def _evalDirectivePatternList(nodes: List[TielNodePattern]) -> None:
    """Evaluate PATTERN node list."""
    for node in nodes:
      if isinstance(node.pattern, str):
        try:
          node.pattern = _regExpr(node.pattern)
        except re.error as error:
          message = f'invalid pattern regular expression `{node.pattern}`'
          raise TielEvalError(message, node.filePath, node.lineNumber) from error

  def _evalDirectiveCallEnd(self,
                            node: TielNodeCall,
                            printFunc: TielPrintFunc) -> None:
    """Evaluate CALL/END CALL node."""
    macroName = node.name.lower()
    macroNode = self._scopeMacros.get(macroName)
    if macroNode is None:
      message = f'macro @{node.name} was not previously defined'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    if node.isConstruct != macroNode.isConstruct:
      if macroNode.isConstruct:
        message = f'macro construct @{node.name} ' \
                  + 'must be called with <call construct> directive'
      else:
        message = f'non-construct macro @{node.name} ' \
                  + 'must be called with <call> directive, not <call construct>'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    # Find a match in macro patterns and evaluate primary section.
    for patternNode in macroNode.patternNodes:
      match = patternNode.pattern.match(node.argument)
      if match is not None:
        self._scope = {**self._scope, **match.groupdict()}
        self._evalNodeList(patternNode.nodes, printFunc)
        break
    else:
      message = f'macro @{macroNode.name} call does not match any pattern'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    # Match and evaluate macro sections.
    #if node.isConstruct:
      # Match call sections and macro sections.
      #raise NotImplementedError()


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tiel_preprocess(filePath: str,
                    output_filePath: str,
                    options: TielOptions = TielOptions()) -> None:
  """Preprocess the source file."""
  with open(filePath, 'r') as fp:
    lines = fp.read().splitlines()
  tree = TielParser(filePath, lines).parse()
  pass


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