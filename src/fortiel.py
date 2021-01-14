#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
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
from os import path
import re
import json
from json import JSONEncoder
from typing import \
  Any, List, Dict, Union, \
  Callable, Optional, Pattern, Match

sys.dont_write_bytecode = True

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielOptions:
  '''Preprocessor options.'''
  def __init__(self) -> None:
    self.includePaths: List[str] = []


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielError(Exception):
  '''Preprocessor syntax tree parse error.'''
  def __init__(self, message: str, filePath: str, lineNumber: int) -> None:
    super().__init__()
    self.message: str = message
    self.filePath: str = filePath
    self.lineNumber: int = lineNumber

  def __str__(self) -> str:
    message = f'{self.filePath}:{self.lineNumber}:1:\n\n' \
              + f'Fatal Error: {self.message}'
    return ''.join(message)


class TielDirError(TielError):
  '''Unexpected directive preprocessor error.'''


class TielEvalError(TielError):
  '''Error in the directive or line substitution evaluation.'''


class TielFileError(TielEvalError):
  '''Error in the include file path.'''


class TielTypeError(TielError):
  '''Type error in the expression.'''


class TielEndError(TielError):
  '''Unexpected end of file preprocessor error.'''
  def __init__(self, filePath: str, lineNumber: int):
    super().__init__('unexpected end of file', filePath, lineNumber)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


class TielTree:
  '''Preprocessor syntax tree.'''
  def __init__(self, filePath: str) -> None:
    self.filePath: str = filePath
    self.rootNodeList: List[TielNode] = []

  def __str__(self) -> str:
    class Encoder(JSONEncoder):
      def default(self, obj):
        return obj.__dict__

    string = json.dumps(self, indent=2, cls=Encoder)
    return string


class TielNode:
  '''Preprocessor syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    self.filePath: str = filePath
    self.lineNumber: int = lineNumber


class TielNodeLineList(TielNode):
  '''The list of regular lines syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.lineList: List[str] = []


class TielNodeUse(TielNode):
  '''The USE/INCLUDE directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.headerFilePath: str = ''
    self.doPrintLines: bool = False


class TielNodeLet(TielNode):
  '''The LET directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.arguments: Optional[str] = None
    self.expression: str = ''


class TielNodeUndef(TielNode):
  '''The UNDEF directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.nameList: List[str] = []


class TielNodeIfEnd(TielNode):
  '''The IF/ELSE IF/ELSE/END IF directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.condition: str = ''
    self.thenNodeList: List[TielNode] = []
    self.elseIfNodeList: List[TielNodeElseIf] = []
    self.elseNodeList: List[TielNode] = []


class TielNodeElseIf(TielNode):
  '''The ELSE IF directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.condition: str = ''
    self.nodeList: List[TielNode] = []


class TielNodeDoEnd(TielNode):
  '''The DO/END DO directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.indexName: str = ''
    self.bounds: str = ''
    self.nodeList: List[TielNode] = []


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def _regExpr(pattern: str) -> Pattern[str]:
  return re.compile(pattern, re.IGNORECASE)


_DIR = _regExpr(r'^\s*#fpp\s+(?P<dir>.*)$')
_DIR_HEAD = _regExpr(r'^(?P<head>\w+)(\s+(?P<head2>\w+))?')

_USE = _regExpr(r'^(?P<dir>use|include)\s+' +
                r'(?P<path>(?:\".+\")|(?:\'.+\')|(?:\<.+\>))$')

_LET = _regExpr(r'^let\s+(?P<name>[a-zA-Z]\w*)\s*' +
                r'(?P<args>\((?:[a-zA-Z]\w*(?:\s*,\s*[a-zA-Z]\w*)*)?\s*\))?\s*' +
                r'=\s*(?P<expr>.*)$')

_UNDEF = _regExpr(r'^undef\s+(?P<names>[a-zA-Z]\w*(?:\s*,\s*[a-zA-Z]\w*)*)$')

_IF = _regExpr(r'^if\s*(?P<cond>.+)$')
_ELSE_IF = _regExpr(r'^else\s*if\s*(?P<cond>.+)$')
_ELSE = _regExpr(r'^else$')
_END_IF = _regExpr(r'^end\s*if$')

_DO = _regExpr(r'^do\s+(?P<index>[a-zA-Z]\w*)\s*=\s*(?P<bounds>.*)$')
_END_DO = _regExpr(r'^end\s*do$')

_LINE = _regExpr(r'(line)?\s*(?P<num>\d+)\s+(?P<path>(\'.+\')|(\".+\"))')


class TielParser:
  '''Preprocessor syntax tree parser.'''
  def __init__(self,
               filePath: str, lines: List[str]) -> None:
    self._filePath: str = filePath
    self._lines: List[str] = lines
    self._curLine: str = self._lines[0]
    self._curLineIndex: int = 0
    self._curLineNumber: int = 1

  def _matchesEnd(self) -> bool:
    return self._curLineIndex >= len(self._lines)

  def _advanceLine(self) -> None:
    self._curLineIndex += 1
    self._curLineNumber += 1
    self._curLine: str = '' if self._matchesEnd() \
      else self._lines[self._curLineIndex].rstrip()

  def _matchesLine(self, *regExpList: Pattern[str]) -> Optional[Match[str]]:
    if self._matchesEnd():
      raise TielEndError(self._filePath, self._curLineNumber)
    for regExp in regExpList:
      match = regExp.match(self._curLine)
      if match is not None:
        return match
    return None

  def _matchLine(self, regExp: Pattern[str]) -> Match[str]:
    match = self._matchesLine(regExp)
    if match is None:
      raise RuntimeError('expected match')
    self._advanceLine()
    return match

  def _matchesLineCont(self) -> bool:
    return self._curLine.endswith('&')

  def _parseLineCont(self) -> None:
    while self._matchesLineCont():
      self._curLine = self._curLine[:-1].rstrip()
      self._curLineIndex += 1
      self._curLineNumber += 1
      if self._matchesEnd():
        raise TielEndError(self._filePath, self._curLineNumber)
      nextLine = self._lines[self._curLineIndex].strip()
      if nextLine.startswith('&'):
        nextLine = nextLine[1:].lstrip()
      self._curLine += ' ' + nextLine

  @staticmethod
  def _getHead(directive: str) -> str:
    # ELSE is merged with IF,
    # END is merged with any following word.
    dirHead, dirHead2 \
      = _DIR_HEAD.match(directive).group('head', 'head2')
    dirHead = dirHead.lower()
    if dirHead2 is not None:
      dirHead2 = dirHead2.lower()
      if dirHead == 'end' or dirHead == 'else' and dirHead2 == 'if':
        dirHead += dirHead2
    return dirHead

  def _matchesDirHead(self, *dirHeadList: str) -> Optional[str]:
    self._parseLineCont()
    dirMatch = self._matchesLine(_DIR)
    if dirMatch is not None:
      directive = dirMatch['dir'].lower()
      dirHead = type(self)._getHead(directive)
      if dirHead in dirHeadList:
        return dirHead
    return None

  def _matchDirective(self, regExp: Pattern[str]) -> Match[str]:
    directive = self._matchLine(_DIR).group('dir').rstrip()
    match = regExp.match(directive)
    if match is None:
      dirHead = type(self)._getHead(directive)
      message = f'invalid <{dirHead}> directive syntax'
      raise TielDirError(message, self._filePath, self._curLineNumber)
    return match

  def parse(self) -> TielTree:
    '''Parse the source lines.'''
    tree = TielTree(self._filePath)
    while not self._matchesEnd():
      tree.rootNodeList.append(self._parseSingle())
    return tree

  def _parseSingle(self) -> TielNode:
    '''Parse a directive or a line block.'''
    if self._matchesLine(_DIR):
      return self._parseDirective()
    return self._parseLineList()

  def _parseLineList(self) -> TielNodeLineList:
    '''Parse a line list.'''
    node = TielNodeLineList(self._filePath,
                            self._curLineNumber)
    while True:
      node.lineList.append(self._curLine)
      self._advanceLine()
      if self._matchesEnd() or self._matchesLine(_DIR):
        break
    return node

  def _parseDirective(self) -> TielNode:
    '''Parse a directive.'''
    self._parseLineCont()
    directive = self._matchesLine(_DIR)['dir']
    dirHead = type(self)._getHead(directive)
    if dirHead == 'use' \
        or dirHead == 'include':
      return self._parseDirectiveUse()
    if dirHead == 'let':
      return self._parseDirectiveLet()
    if dirHead == 'undef':
      return self._parseDirectiveUndef()
    if dirHead == 'if':
      return self._parseDirectiveIfEnd()
    if dirHead == 'do':
      return self._parseDirectiveDoEnd()
    if dirHead == 'line' or dirHead.isdecimal():
      self._parseDirectiveLine()
      return self._parseSingle()
    # Determine the error type:
    # either the known directive is misplaced,
    # either the directive is unknown.
    if dirHead in ['else', 'elseif', 'endif', 'enddo']:
      message = f'misplaced directive <{dirHead}>'
      raise TielDirError(message, self._filePath, self._curLineNumber)
    else:
      message = f'unknown or mistyped directive <{dirHead}>'
      raise TielDirError(message, self._filePath, self._curLineNumber)

  def _parseDirectiveUse(self) -> TielNodeUse:
    '''Parse USE/INCLUDE directives.'''
    node = TielNodeUse(self._filePath,
                       self._curLineNumber)
    directive, node.headerFilePath \
      = self._matchDirective(_USE).group('dir', 'path')
    node.headerFilePath = node.headerFilePath[1:-1]
    if directive.lower() == 'include':
      node.doPrintLines = True
    return node

  def _parseDirectiveLet(self) -> TielNodeLet:
    '''Parse LET directive.'''
    # Note that we are not
    # evaluating or validating define arguments and body here.
    node = TielNodeLet(self._filePath,
                       self._curLineNumber)
    node.name, node.arguments, node.expression \
      = self._matchDirective(_LET).group('name', 'args', 'expr')
    if node.arguments is not None:
      node.arguments = node.arguments[1:-1].strip()
    return node

  def _parseDirectiveUndef(self) -> TielNodeUndef:
    '''Parse UNDEF directive.'''
    # Note that we are not
    # evaluating or validating define name here.
    node = TielNodeUndef(self._filePath,
                         self._curLineNumber)
    nameList = self._matchDirective(_UNDEF).group('names')
    node.nameList = [name.strip() for name in nameList.split(',')]
    return node

  def _parseDirectiveIfEnd(self) -> TielNodeIfEnd:
    '''Parse IF/ELSE IF/ELSE/END IF directives.'''
    # Note that we are not
    # evaluating or validating conditions here.
    node = TielNodeIfEnd(self._filePath,
                         self._curLineNumber)
    node.condition = self._matchDirective(_IF)['cond']
    while not self._matchesDirHead('elseif', 'else', 'endif'):
      node.thenNodeList.append(self._parseSingle())
    if self._matchesDirHead('elseif'):
      while not self._matchesDirHead('else', 'endif'):
        elseIfNode = TielNodeElseIf(self._filePath,
                                    self._curLineNumber)
        elseIfNode.condition = self._matchDirective(_ELSE_IF)['cond']
        while not self._matchesDirHead('elseif', 'else', 'endif'):
          elseIfNode.nodeList.append(self._parseSingle())
        node.elseIfNodeList.append(elseIfNode)
    if self._matchesDirHead('else'):
      self._matchDirective(_ELSE)
      while not self._matchesDirHead('endif'):
        node.elseNodeList.append(self._parseSingle())
    self._matchDirective(_END_IF)
    return node

  def _parseDirectiveDoEnd(self) -> TielNodeDoEnd:
    '''Parse DO/END DO directives.'''
    # Note that we are not
    # evaluating or validating loop bounds here.
    node = TielNodeDoEnd(self._filePath,
                         self._curLineNumber)
    node.indexName, node.bounds \
      = self._matchDirective(_DO).group('index', 'bounds')
    while not self._matchesDirHead('enddo'):
      node.nodeList.append(self._parseSingle())
    self._matchDirective(_END_DO)
    return node

  def _parseDirectiveLine(self) -> None:
    '''Parse LINE directive.'''
    self._filePath, self._curLineNumber \
      = self._matchDirective(_LINE).group('path', 'num')
    self._filePath = self._filePath[1:-1]
    self._curLineNumber = int(self._curLineNumber)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_BUILTIN_NAMES = [
  '__FILE__', '__LINE__',
  '__DATE__', '__TIME__',
  '__INDEX__',
]


class TielEvaluator:
  '''Abstract syntax tree evaluator.'''
  def __init__(self, options: TielOptions):
    self._scope: Dict[str, Any] = {}
    self._options: TielOptions = options

  def eval(self,
           tree: TielTree,
           printFunc: Callable[[str], None]) -> None:
    '''Evaluate the syntax tree or the syntax tree node.'''
    printFunc(f'# 1 "{tree.filePath}"')
    self._evalNodeList(tree.rootNodeList, printFunc)

  def _evalExpr(self,
                expression: str,
                filePath: str, lineNumber: int):
    '''Evaluate macro expression.'''
    try:
      result = eval(expression, self._scope)
    except Exception as error:
      message = f'expression evaluation exception `{str(error)}`'
      raise TielEvalError(message, filePath, lineNumber) from error
    return result

  def _evalNodeList(self,
                    nodes: List[TielNode],
                    printFunc: Callable[[str], None]) -> None:
    '''Evaluate the syntax tree node or a list of nodes.'''
    for node in nodes:
      if isinstance(node, TielNodeLineList):
        self._evalLineList(node, printFunc)
      elif isinstance(node, TielNodeUse):
        self._evalUse(node, printFunc)
      elif isinstance(node, TielNodeLet):
        self._evalLet(node)
      elif isinstance(node, TielNodeUndef):
        self._evalUndef(node)
      elif isinstance(node, TielNodeIfEnd):
        self._evalIfElseEnd(node, printFunc)
      elif isinstance(node, TielNodeDoEnd):
        self._evalDoEnd(node, printFunc)
      else:
        nodeType = node.__class__.__name__
        raise RuntimeError(f'no evaluator for node type {nodeType}')

  def _evalLine(self,
                line: str,
                filePath: str, lineNumber: int,
                printFunc: Callable[[str], None]) -> None:
    '''Evaluate in-line substitutions.'''
    # Evaluate <{}> substitutions.
    def lineSub(match: Match[str]) -> str:
      expression = match['expr']
      return str(self._evalExpr(expression, filePath, lineNumber))
    line = re.sub(r'{(?P<expr>.+)}', lineSub, line)
    # Evaluate <@:> substitutions.
    def loopSub(match: Match[str]) -> str:
      expression = match['expr']
      index = self._scope.get('__INDEX__')
      if index is None:
        message = '<@:> substitution outside of the <do> loop body'
        raise TielEvalError(message, filePath, lineNumber)
      return str(index * expression)
    line = re.sub(r'@(?P<expr>:(\s*,)?)', loopSub, line)
    printFunc(line)

  def _evalLineList(self,
                    node: TielNodeLineList,
                    printFunc: Callable[[str], None]) -> None:
    '''Evaluate line block.'''
    for lineNumber, line in enumerate(node.lineList, start=node.lineNumber):
      self._evalLine(line, node.filePath, lineNumber, printFunc)

  @staticmethod
  def _findFile(filePath: str, dirPathList: List[str]) -> Optional[str]:
    if path.exists(filePath):
      return filePath
    for dirPath in dirPathList:
      filePathInDir = path.join(dirPath, filePath)
      if path.exists(filePathInDir):
        return filePathInDir
    return None

  def _evalUse(self,
               node: TielNodeUse,
               printFunc: Callable[[str], None]) -> None:
    '''Evaluate USE/INCLUDE directive.'''
    curDirPath, _ = path.split(node.filePath)
    headerFilePath \
      = type(self)._findFile(node.headerFilePath,
                             self._options.includePaths + [curDirPath])
    if headerFilePath is None:
      message = f'`{node.headerFilePath}`: no such file or directory'
      raise TielFileError(message, node.filePath, node.lineNumber)
    if path.isdir(headerFilePath):
      message = f'`{node.headerFilePath}`: is a directory, file expected'
      raise TielFileError(message, node.filePath, node.lineNumber)
    with open(headerFilePath, mode='r') as fp:
      headerLines = fp.read().splitlines()
    headerTree = TielParser(node.headerFilePath, headerLines).parse()
    if node.doPrintLines:
      self.eval(headerTree, printFunc)
    else:
      dummyPrintFunc = lambda _: None
      self.eval(headerTree, dummyPrintFunc)

  def _evalLet(self,
               node: TielNodeLet) -> None:
    '''Evaluate LET directive.'''
    if node.name in self._scope:
      message = f'name `{node.name}` is already defined.'
      raise TielEvalError(message, node.filePath, node.lineNumber)
    if node.name in _BUILTIN_NAMES:
        message = f'builtin name <{node.name}> can not be redefined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
    if node.arguments is None:
      value = self._evalExpr(node.expression,
                             node.filePath, node.lineNumber)
      self._scope[node.name] = value
    else:
      argNameList = [arg.strip() for arg in node.arguments.split(',')]
      if len(argNameList) > len(set(argNameList)):
        message = 'functional <let> arguments must be unique'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      # Evaluate functional LET as lambda function.
      expression = f'lambda {node.arguments}: {node.expression}'
      func = self._evalExpr(expression,
                            node.filePath, node.lineNumber)
      self._scope[node.name] = func

  def _evalUndef(self,
                 node: TielNodeUndef) -> None:
    '''Evaluate UNDEF directive.'''
    for name in node.nameList:
      if not name in self._scope:
        message = f'name `{name}` was not previously defined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      if name in _BUILTIN_NAMES:
        message = f'builtin name <{name}> can not be undefined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      del self._scope[name]

  def _evalIfElseEnd(self,
                     node: TielNodeIfEnd,
                     printFunc: Callable[[str], None]) -> None:
    '''Evaluate IF/ELSE IF/ELSE/END IF node.'''
    if self._evalExpr(node.condition,
                      node.filePath, node.lineNumber):
      self._evalNodeList(node.thenNodeList, printFunc)
    else:
      for elseIfNode in node.elseIfNodeList:
        if self._evalExpr(elseIfNode.condition,
                          elseIfNode.filePath, elseIfNode.lineNumber):
          self._evalNodeList(elseIfNode.nodeList, printFunc)
          break
      else:
        self._evalNodeList(node.elseNodeList, printFunc)

  def _evalDoEnd(self,
                 node: TielNodeDoEnd,
                 printFunc: Callable[[str], None]) -> None:
    '''Evaluate DO/END DO node.'''
    bounds = self._evalExpr(node.bounds,
                            node.filePath, node.lineNumber)
    if not isinstance(bounds, tuple) \
        or not (2 <= len(bounds) <= 3) \
        or list(map(type, bounds)) != len(bounds) * [int]:
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
      self._evalNodeList(node.nodeList, printFunc)
    del self._scope[node.indexName]
    if prevIndex is not None:
      self._scope['__INDEX__'] = prevIndex
    else:
      del self._scope['__INDEX__']


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tielPreprocess(filePath: str,
                   outputFilePath: str,
                   options: TielOptions=TielOptions()) -> None:
  '''Preprocess the source file.'''
  with open(filePath, 'r') as fp:
    lines = fp.read().splitlines()
  tree = TielParser(filePath, lines).parse()
  with open(outputFilePath, 'w') as fp:
    printFunc = lambda line: print(line, file=fp)
    TielEvaluator(options).eval(tree, printFunc)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tielMain() -> None:
  filePath = sys.argv[1]
  outputFilePath = sys.argv[2]
  tielPreprocess(filePath, outputFilePath)


if __name__ == '__main__':
  tielMain()
