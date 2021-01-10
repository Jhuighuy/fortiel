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


_DIR = _regExpr(r'^\s*#\s*fpp\s+(?P<dir>(?P<head>\w+).*\b)\s*(!.*)?$')
_DIR2 = _regExpr(r'^#\s*fpp\s+(?P<head>\w+\s+\w+)(\s+.+)?(\s+\!.*)?$')

_IF = _regExpr(r'^if\s*\((?P<cond>.+)\)\s*then$')
_ELSE_IF = _regExpr(r'^else\s*if\s*\((?P<cond>.+)\)\s*then$')
_ELSE = _regExpr(r'^else$')
_END_IF = _regExpr(r'^end\s*if$')

_DO = _regExpr(r'^do\s+(?P<index>[a-zA-Z]\w*)\s*=\s*(?P<bounds>.*)$')
_END_DO = _regExpr(r'^end\s*do$')

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
    dirHead, dirHead2 = re.match(r'^(?P<head>\w+)(\s+(?P<head2>\w+))?',
                                 directive).group('head', 'head2')
    dirHead = dirHead.lower()
    # ELSE is merged with IF,
    # END is merged with any following word.
    if dirHead2 is not None:
      dirHead2 = dirHead2.lower()
      if dirHead == 'end' \
        or dirHead == 'else' and dirHead2 == 'if':
        dirHead += dirHead2
    return dirHead

  def _matchDirective(self, regExp: Pattern[str]) -> Match[str]:
    directive = self._matchLine(_DIR).group('dir')
    match = regExp.match(directive)
    if match is None:
      dirHead = self.__class__._getHead(directive)
      raise TielDirError(f'invalid <{dirHead}> directive syntax',
                         self._filePath, self._curLineNumber)
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
    if dirHead in ['use', 'include']:
      return self._parseDirectiveUse()
    if dirHead == 'line' or dirHead.isdecimal():
      self._parseDirectiveLine()
      return self._parseSingle()
    # Determine the error type:
    # either the known directive is misplaced,
    # either the directive is unknown.
    if dirHead in ['else', 'elseif', 'endif', 'enddo']:
      raise TielDirError(f'misplaced directive <{dirHead}>',
                         self._filePath, self._curLineNumber)
    else:
      raise TielDirError(f'unknown directive <{dirHead}>',
                         self._filePath, self._curLineNumber)

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


class TielEvaluator:
  '''Abstract syntax tree evaluator.'''
  def __init__(self, scope=None):
    if scope is None:
      scope = {}
    self._scope: Dict[str, Any] = scope

  def eval(self,
           nodeOrTree: Union[TielTree, TielTreeNode],
           callback: Callable[[str], None]) -> None:
    '''Evaluate the syntax tree or the syntax tree node.'''
    if isinstance(nodeOrTree, TielTree):
      tree: TielTree = nodeOrTree
      self._evalNodeList(tree.rootNodes, callback)
    else:
      node: TielTreeNode = nodeOrTree
      self._evalNodeList(node, callback)

  def _evalExpr(self,
                expression: str,
                filePath: str, lineNumber: int,
                type=None):
    '''Evaluate macro expression.'''
    try:
      result = eval(expression, dict(self._scope))
    except NameError as nameError:
      raise
    except TypeError as typeError:
      raise
    except ArithmeticError as error:
      raise TielEvalError(str(error.args),
                          filePath, lineNumber)
    if type is not None:
      try:
        result = type(result)
      except (TypeError, ValueError) as error:
        raise
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
      elif isinstance(node, TielTreeNodeUse):
        self._evalUse(node, callback)
      else:
        raise RuntimeError(node.__class__.__name__)

  def _evalLineBlock(self,
                     node: TielTreeNodeLineBlock,
                     callback: Callable[[str], None]) -> None:
    '''Evaluate line block.'''
    callback(f'# {node.lineNumber} "{node.filePath}"')
    for lineNumber, line in enumerate(node.lines, start=node.lineNumber):
      self._evalLine(line, node.filePath, lineNumber, callback)

  def _evalLine(self,
                line: str,
                filePath: str, lineNumber: int,
                callback: Callable[[str], None]) -> None:
    '''Evaluate in-line substitutions.'''
    line = re.sub(r'{(?P<expr>.+)}',
                  lambda match:
                    str(self._evalExpr(match['expr'],
                                       filePath, lineNumber)),
                  line)
    line = re.sub(r'@(?P<expr>:(\s*,)?)',
                  lambda match:
                    str(self._scope['__INDEX__']*match['expr']),
                  line)
    callback(line)

  def _evalIfElseEnd(self,
                     node: TielTreeNodeIfElseEnd,
                     callback: Callable[[str], None]) -> None:
    '''Evaluate IF/ELSE IF/ELSE/END IF node.'''
    condition = self._evalExpr(node.condition,
                               node.filePath, node.lineNumber,
                               type=bool)
    if condition:
      self._evalNodeList(node.thenBranch, callback)
    else:
      for elseIfNode in node.elseIfBranches:
        condition \
          = self._evalExpr(elseIfNode.condition,
                           elseIfNode.filePath, elseIfNode.lineNumber,
                           type=bool)
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
        or list(map(type, bounds)) != len(bounds)*[int]:
      raise TielEvalError('tuple of two or three integers ' +
                          'inside `do` directive bounds is expected, ' +
                          f' got `{node.bounds}`',
                          node.filePath, node.lineNumber)
    start, stop = bounds[0:2]
    step = bounds[2] if len(bounds) == 3 else 1
    for index in range(start, stop+1, step):
      self._scope[node.indexName] = index
      self._scope['__INDEX__'] = index
      self._evalNodeList(node.loopBody, callback)
    del self._scope[node.indexName]
    del self._scope['__INDEX__']

  def _evalUse(self,
               node: TielTreeNodeUse,
               callback: Callable[[str], None]) -> None:
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
    scope = {'NumRanks': 1}
    TielEvaluator(dict(scope)).eval(tree,
                                    lambda x: print(x, file=fp))


# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #

def tielMain() -> None:
  filePath = sys.argv[1]
  outputFilePath = sys.argv[2]
  tielPreprocess(filePath, outputFilePath)


if __name__ == '__main__':
  tielMain()
