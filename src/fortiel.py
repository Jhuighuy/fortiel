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
import re
import json
from json import JSONEncoder
from typing import \
  Any, List, Dict, Union, \
  Callable, Optional, Pattern, Match

sys.dont_write_bytecode = True


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
  '''Error in the expression.'''


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
    self.rootNodes: List[TielTreeNode] = []

  def __str__(self) -> str:
    class Encoder(JSONEncoder):
      def default(self, obj):
        return obj.__dict__

    string = json.dumps(self, indent=2, cls=Encoder)
    return string


class TielTreeNode:
  '''Preprocessor syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    self.filePath: str = filePath
    self.lineNumber: int = lineNumber


class TielTreeNodeLineBlock(TielTreeNode):
  '''The block of regular lines syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.lines: List[str] = []


class TielTreeNodeIfElseEnd(TielTreeNode):
  '''The IF/ELSE IF/ELSE/END IF directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.condition: str = ''
    self.thenBranch: List[TielTreeNode] = []
    self.elseIfBranches: List[TielTreeNodeElseIf] = []
    self.elseBranch: List[TielTreeNode] = []


class TielTreeNodeElseIf(TielTreeNode):
  '''The ELSE IF directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.condition: str = ''
    self.branch: List[TielTreeNode] = []


class TielTreeNodeDoEnd(TielTreeNode):
  '''The DO/END DO directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.indexName: str = ''
    self.bounds: str = ''
    self.loopBody: List[TielTreeNode] = []


class TielTreeNodeLet(TielTreeNode):
  '''The LET directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.name: str = ''
    self.arguments: Optional[str] = None
    self.expression: str = ''


class TielTreeNodeUndef(TielTreeNode):
  '''The UNDEF directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.nameList: List[str] = []


class TielTreeNodeUse(TielTreeNode):
  '''The USE/INCLUDE directive syntax tree node.'''
  def __init__(self, filePath: str, lineNumber: int) -> None:
    super().__init__(filePath, lineNumber)
    self.pathToInclude: str = ''
    self.emitLineBlocks: bool = False


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def _regExpr(pattern: str) -> Pattern[str]:
  return re.compile(pattern, re.IGNORECASE)


_DIR = _regExpr(r'^\s*#\s*fpp\s+(?P<dir>.*)$')
_DIR_HEAD = _regExpr(r'^(?P<head>\w+)(\s+(?P<head2>\w+))?')

_IF = _regExpr(r'^if\s*(?P<cond>.+)$')
_ELSE_IF = _regExpr(r'^else\s*if\s*(?P<cond>.+)$')
_ELSE = _regExpr(r'^else$')
_END_IF = _regExpr(r'^end\s*if$')

_DO = _regExpr(r'^do\s+(?P<index>[a-zA-Z]\w*)\s*=\s*(?P<bounds>.*)$')
_END_DO = _regExpr(r'^end\s*do$')

_LET = _regExpr(r'^let\s+(?P<name>[a-zA-Z]\w*)\s*' \
                + r'(?P<args>\((?:[a-zA-Z]\w*(?:\s*,\s*[a-zA-Z]\w*)*)?\s*\))?\s*'
                + r'=\s*(?P<expr>.*)$')
_UNDEF = _regExpr(r'^undef\s+(?P<names>[a-zA-Z]\w*(?:\s*,\s*[a-zA-Z]\w*)*)$')

_USE = _regExpr(r'^(?P<dir>use|include)\s+(?P<path>(\".+\")|(\'.+\')|(\<.+\>))$')

_LINE = _regExpr(r'(line)?\s*(?P<num>\d+)\s+(?P<path>(\'.+\')|(\".+\"))')


class TielParser:
  '''Preprocessor syntax tree parser.'''
  def __init__(self,
               filePath: str, lines: List[str]) -> None:
    self._filePath: str = filePath
    self._lines: List[str] = lines
    self._curLineIndex: int = 0
    self._curLineNumber: int = 1

  def _curLine(self) -> str:
    return self._lines[self._curLineIndex]

  def _advanceLine(self) -> None:
    self._curLineIndex += 1
    self._curLineNumber += 1

  def _matchesEnd(self) -> bool:
    return self._curLineIndex >= len(self._lines)

  def _matchLine(self, regExp: Pattern[str]) -> Match[str]:
    match = self._matchesLine(regExp)
    if match is None:
      raise RuntimeError('expected match')
    self._advanceLine()
    return match

  def _matchesLine(self, *regExpList: Pattern[str]) -> Optional[Match[str]]:
    if self._matchesEnd():
      raise TielEndError(self._filePath, self._curLineNumber)
    for regExp in regExpList:
      match = regExp.match(self._curLine())
      if match is not None:
        return match
    return None

  @staticmethod
  def _getHead(directive: str) -> str:
    # ELSE is merged with IF,
    # END is merged with any following word.
    dirHead, dirHead2 \
      = _DIR_HEAD.match(directive).group('head', 'head2')
    dirHead = dirHead.lower()
    if dirHead2 is not None:
      dirHead2 = dirHead2.lower()
      if dirHead == 'end' \
          or dirHead == 'else' and dirHead2 == 'if':
        dirHead += dirHead2
    return dirHead

  def _matchDirective(self, regExp: Pattern[str]) -> Match[str]:
    directive = self._matchLine(_DIR).group('dir').rstrip()
    match = regExp.match(directive)
    if match is None:
      dirHead = self.__class__._getHead(directive)
      message = f'invalid <{dirHead}> directive syntax'
      raise TielDirError(message, self._filePath, self._curLineNumber)
    return match

  def _matchesDirHead(self, *dirHeadList: str) -> Optional[str]:
    dirMatch = self._matchesLine(_DIR)
    if dirMatch is not None:
      directive = dirMatch['dir'].lower()
      dirHead = self.__class__._getHead(directive)
      if dirHead in dirHeadList:
        return dirHead
    return None

  def parse(self) -> TielTree:
    '''Parse the source lines.'''
    tree = TielTree(self._filePath)
    while not self._matchesEnd():
      tree.rootNodes.append(self._parseSingle())
    return tree

  def _parseSingle(self) -> TielTreeNode:
    '''Parse a directive or a line block.'''
    if self._matchesLine(_DIR):
      return self._parseDirective()
    return self._parseLineBlock()

  def _parseLineBlock(self) -> TielTreeNodeLineBlock:
    '''Parse a line block.'''
    node = TielTreeNodeLineBlock(self._filePath,
                                 self._curLineNumber)
    while True:
      node.lines.append(self._curLine())
      self._advanceLine()
      if self._matchesEnd() or self._matchesLine(_DIR):
        break
    return node

  def _parseDirective(self) -> TielTreeNode:
    '''Parse a directive.'''
    directive = self._matchesLine(_DIR)['dir']
    dirHead = self.__class__._getHead(directive)
    if dirHead == 'if':
      return self._parseDirectiveIfElseEnd()
    if dirHead == 'do':
      return self._parseDirectiveDoEnd()
    if dirHead == 'let':
      return self._parseDirectiveLet()
    if dirHead == 'undef':
      return self._parseDirectiveUndef()
    if dirHead in ['use', 'include']:
      return self._parseDirectiveUse()
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

  def _parseDirectiveIfElseEnd(self) -> TielTreeNodeIfElseEnd:
    '''Parse IF/ELSE IF/ELSE/END IF directives.'''
    # Note that we are not
    # evaluating or validating conditions here.
    node = TielTreeNodeIfElseEnd(self._filePath,
                                 self._curLineNumber)
    node.condition = self._matchDirective(_IF)['cond']
    while not self._matchesDirHead('elseif', 'else', 'endif'):
      node.thenBranch.append(self._parseSingle())
    if self._matchesDirHead('elseif'):
      while not self._matchesDirHead('else', 'endif'):
        elseIfNode = TielTreeNodeElseIf(self._filePath,
                                        self._curLineNumber)
        elseIfNode.condition = self._matchDirective(_ELSE_IF)['cond']
        while not self._matchesDirHead('elseif', 'else', 'endif'):
          elseIfNode.branch.append(self._parseSingle())
        node.elseIfBranches.append(elseIfNode)
    if self._matchesDirHead('else'):
      self._matchDirective(_ELSE)
      while not self._matchesDirHead('endif'):
        node.elseBranch.append(self._parseSingle())
    self._matchDirective(_END_IF)
    return node

  def _parseDirectiveDoEnd(self) -> TielTreeNodeDoEnd:
    '''Parse DO/END DO directives.'''
    # Note that we are not
    # evaluating or validating loop bounds here.
    node = TielTreeNodeDoEnd(self._filePath,
                             self._curLineNumber)
    node.indexName, node.bounds \
      = self._matchDirective(_DO).group('index', 'bounds')
    while not self._matchesDirHead('enddo'):
      node.loopBody.append(self._parseSingle())
    self._matchDirective(_END_DO)
    return node

  def _parseDirectiveLet(self) -> TielTreeNodeLet:
    '''Parse LET directive.'''
    # Note that we are not
    # evaluating or validating define arguments and body here.
    node = TielTreeNodeLet(self._filePath,
                           self._curLineNumber)
    node.name, node.arguments, node.expression \
      = self._matchDirective(_LET).group('name', 'args', 'expr')
    if node.arguments is not None:
      node.arguments = node.arguments[1:-1].strip()
    return node

  def _parseDirectiveUndef(self) -> TielTreeNodeUndef:
    '''Parse UNDEF directive.'''
    # Note that we are not
    # evaluating or validating define name here.
    node = TielTreeNodeUndef(self._filePath,
                             self._curLineNumber)
    nameList = self._matchDirective(_UNDEF).group('names')
    node.nameList = [name.strip() for name in nameList.split(',')]
    return node

  def _parseDirectiveUse(self) -> TielTreeNodeUse:
    '''Parse USE/INCLUDE directives.'''
    node = TielTreeNodeUse(self._filePath,
                           self._curLineNumber)
    directive, node.pathToInclude \
      = self._matchDirective(_USE).group('dir', 'path')
    node.pathToInclude = node.pathToInclude[1:-1]
    if directive.lower() == 'include':
      node.emitLineBlocks = True
    return node

  def _parseDirectiveLine(self) -> None:
    '''Parse LINE directive.'''
    self._filePath, self._curLineNumber \
      = self._matchDirective(_LINE).group('path', 'num')
    self._filePath = self._filePath[1:-1]
    self._curLineNumber = int(self._curLineNumber)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


_BUILTIN_NAMES = ['__FILE__', '__LINE__', '__INDEX__']


class TielEvaluator:
  '''Abstract syntax tree evaluator.'''
  def __init__(self, scope=None):
    if scope is None:
      scope = {}
    self._scope: Dict[str, Any] = scope

  def eval(self,
           tree: TielTree,
           callback: Callable[[str], None]) -> None:
    '''Evaluate the syntax tree or the syntax tree node.'''
    self._evalNodeList(tree.rootNodes, callback)

  def _evalExpr(self,
                expression: str,
                filePath: str, lineNumber: int):
    '''Evaluate macro expression.'''
    try:
      result = eval(expression, self._scope)
    except NameError as error:
      name = 'todo'
      message = f'name `{name}` is not defined'
      raise TielEvalError(message, filePath, lineNumber) from error
    except Exception as error:
      message = f'expression evaluation exception `{str(error)}`'
      raise TielEvalError(message, filePath, lineNumber) from error
    return result

  def _evalNodeList(self,
                    nodes: Union[TielTreeNode, List[TielTreeNode]],
                    callback: Callable[[str], None]) -> None:
    '''Evaluate the syntax tree node or a list of nodes.'''
    if not isinstance(nodes, list):
      nodes = [nodes]
    for node in nodes:
      if isinstance(node, TielTreeNodeLineBlock):
        self._evalLineBlock(node, callback)
      elif isinstance(node, TielTreeNodeIfElseEnd):
        self._evalIfElseEnd(node, callback)
      elif isinstance(node, TielTreeNodeDoEnd):
        self._evalDoEnd(node, callback)
      elif isinstance(node, TielTreeNodeLet):
        self._evalLet(node)
      elif isinstance(node, TielTreeNodeUndef):
        self._evalUndef(node)
      elif isinstance(node, TielTreeNodeUse):
        self._evalUse(node)
      else:
        nodeType = node.__class__.__name__
        raise RuntimeError(f'no evaluator for node type {nodeType}')

  def _evalLine(self,
                line: str,
                filePath: str, lineNumber: int,
                callback: Callable[[str], None]) -> None:
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
    callback(line)

  def _evalLineBlock(self,
                     node: TielTreeNodeLineBlock,
                     callback: Callable[[str], None]) -> None:
    '''Evaluate line block.'''
    callback(f'# {node.lineNumber} "{node.filePath}"')
    for lineNumber, line in enumerate(node.lines, start=node.lineNumber):
      self._evalLine(line, node.filePath, lineNumber, callback)

  def _evalIfElseEnd(self,
                     node: TielTreeNodeIfElseEnd,
                     callback: Callable[[str], None]) -> None:
    '''Evaluate IF/ELSE IF/ELSE/END IF node.'''
    condition = self._evalExpr(node.condition,
                               node.filePath, node.lineNumber)
    if condition:
      self._evalNodeList(node.thenBranch, callback)
    else:
      for elseIfNode in node.elseIfBranches:
        condition = self._evalExpr(elseIfNode.condition,
                                   elseIfNode.filePath, elseIfNode.lineNumber)
        if condition:
          self._evalNodeList(elseIfNode.branch, callback)
          break
      else:
        self._evalNodeList(node.elseBranch, callback)

  def _evalDoEnd(self,
                 node: TielTreeNodeDoEnd,
                 callback: Callable[[str], None]) -> None:
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
      self._evalNodeList(node.loopBody, callback)
    del self._scope[node.indexName]
    if prevIndex is not None:
      self._scope['__INDEX__'] = prevIndex
    else:
      del self._scope['__INDEX__']

  def _evalLet(self,
               node: TielTreeNodeLet) -> None:
    '''Evaluate LET directive.'''
    if node.name in self._scope:
      message = f'name `{node.name}` is already defined'
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
      func = self._evalExpr(f'lambda {node.arguments}: {node.expression}',
                            node.filePath, node.lineNumber)
      self._scope[node.name] = func

  def _evalUndef(self,
                 node: TielTreeNodeUndef) -> None:
    '''Evaluate UNDEF directive.'''
    for name in node.nameList:
      if not name in self._scope:
        message = f'name `{name}` was not previously defined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      if name in _BUILTIN_NAMES:
        message = f'builtin name <{name}> can not be undefined'
        raise TielEvalError(message, node.filePath, node.lineNumber)
      del self._scope[name]

  def _evalUse(self,
               node: TielTreeNodeUse) -> None:
    '''Evaluate USE/INCLUDE directive.'''
    print(node.__class__.__name__)


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tielPreprocess(filePath: str,
                   outputFilePath: str) -> None:
  '''Preprocess the source file.'''
  with open(filePath, 'r') as fp:
    lines = fp.read().splitlines()
  tree = TielParser(filePath, lines).parse()
  with open(outputFilePath, 'w') as fp:
    TielEvaluator().eval(tree,
                         lambda x: print(x, file=fp))


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #


def tielMain() -> None:
  filePath = sys.argv[1]
  outputFilePath = sys.argv[2]
  tielPreprocess(filePath, outputFilePath)


if __name__ == '__main__':
  tielMain()
