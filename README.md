# fortiel — Fortran preprocessor and metaprogramming engine

Fortiel (_mixed [Fortran](https://fortran-lang.org/) 
and [Cockatiel](https://en.wikipedia.org/wiki/Cockatiel)_) 
is a Fortran preprocessor. 


# Installation
Fortiel can be install as the 
[PyPI package](https://pypi.org/project/fortiel/):
```bash
pip3 install fortiel
```


# Preprocessor language


## Directives
Common directive syntax is:
```fortran
#fpp directiveName directiveArguments
```
where `directiveName` is one of the known preprocessor directives.
The `#fpp` directive header is treated as a single token, so no
whitespaces are allowed between `#` and `fpp`.

Both `fpp` and `directiveName` are _case-insensitive_
(Python expressions and file paths although are _case-sensitive_), 
so the following lines are equivalent:
```fortran
#fpp use 'filename'
! and
#FpP uSe 'filename'
```


### Continuation Lines
Fortran-style continuation lines `&` are supported within 
the preprocessor directives:
```fortran
#fpp directivePart &
        anotherDirectivePart
! and
#fpp directivePart &
        & anotherDirectivePart
```


### `include` directive
directly the contents of the file 
located at `filePath` into the current source:
```fortran
#fpp include 'filePath'
! or
#fpp include "filePath"
! or
#fpp include <filePath>
```


### `use` directive
is the same as `include`, but it skips the
non-directive lines:
```fortran
#fpp use 'filePath'
! or
#fpp use "filePath"
! or
#fpp use <filePath>
```


### `let` directive
declares a new named variable:
```fortran
#fpp let var = expression
```
`expression` should be a valid Python 3 expression, 
that may refer to the previously defined variables, 
Fortiel builtins and Python 3 builtins.

Functions can be also declared using the `let` directive:
```fortran
#fpp let fun([argument[, anotherArgument]*]) = expression
```


### `undef` directive
undefines the names, previously defined with 
the `let` directive:
```fortran
#fpp undef var[, anotherVar]*
```
Builtin names like `__FILE__` or `__LINE__` cannot be undefined.


### `if`/`else if`/`else`/`end if` directive
is a classic conditional directive:
```fortran
#fpp if condition
  ! Fortran code.
#fpp else if condition
  ! Fortran code.
#fpp else
  ! Fortran code.
#fpp end if
```
Note that `else if`, `elseif` and `elif` directives, 
`end if` and `endif` directives are respectively equivalent.


### `do`/`end do` directive
substitutes the source lines multiple times:
```fortran 
#fpp do var = first, last[, step]
  ! Fortran code.
#fpp end do
```
`first`, `last` and optional `step` expressions should 
evaluate to integers.
Inside the loop body a special integer variable `__INDEX__` is 
defined, which is equal to the the current value of `var`.

Note that `end do` and `enddo` directives are equivalent.


### `line` directive
changes current line number and file path:
```fortran
#fpp [line] lineNumber 'filePath'
! or
#fpp [line] lineNumber "filePath"
```


## In-line substitutions


### `` `x` `` substitutions
Consider the example:
```fortran
#fpp let x = 'b'
a`x`   ! evaluates to ab;
`3*x`a ! evaluates to bbba.
```


### `@x` substitution
is a special substitution that becomes handy inside 
the `#fpp do` loops:
```fortran
@var[,]
! or
@:[,]
```
This substitution spawns the token after `@` (an identifier 
or colon character), and an optional trailing comma,
the `__INDEX__` amount of times.

Consider the example:
```fortran
#fpp do i = 0, 2
@a, b
#fpp end do
! evaluates to
b
a, b
a, a, b
```


# Examples


## Generic programming
```fortran
module Distances
    
  implicit none

#fpp let NUM_RANKS = 2

  interface computeSquareDistance
#fpp do rank = 0, NUM_RANKS
    module procedure computeSquareDistance{rank}
#fpp end do    
  end interface computeSquareDistance

contains

#fpp do rank = 0, NUM_RANKS
  function computeSquareDistance`rank`(n, u, v) result(d)
    integer, intent(in) :: n
    real, intent(in) :: u(@:,:), v(@:,:)
    real :: d
    integer :: i
    d = 0.0
    do i = 1, n
    #fpp if rank == 0
      d = d + (u(i) - v(i))**2
    #fpp else
      d = d + sum((u(@:,i) - v(@:,i))**2)
    #fpp end if
    end do
  end function computeSquareDistance`rank`
#fpp end do    

end module Distances
```

```fortran
module Distances
    
  implicit none

  interface computeSquareDistance
    module procedure computeSquareDistance0
    module procedure computeSquareDistance1
    module procedure computeSquareDistance2
  end interface computeSquareDistance

contains

  function computeSquareDistance0(n, u, v) result(d)
    integer, intent(in) :: n
    real, intent(in) :: u(:), v(:)
    real :: d
    integer :: i
    d = 0.0
    do i = 1, n
      d = d + (u(i) - v(i))**2
    end do
  end function computeSquareDistance0
  function computeSquareDistance1(n, u, v) result(d)
    integer, intent(in) :: n
    real, intent(in) :: u(:,:), v(:,:)
    real :: d
    integer :: i
    d = 0.0
    do i = 1, n
      d = d + sum((u(:,i) - v(:,i))**2)
    end do
  end function computeSquareDistance1
  function computeSquareDistance2(n, u, v) result(d)
    integer, intent(in) :: n
    real, intent(in) :: u(:,:,:), v(:,:,:)
    real :: d
    integer :: i
    d = 0.0
    do i = 1, n
      d = d + sum((u(:,:,i) - v(:,:,i))**2)
    end do
  end function computeSquareDistance2

end module Distances
```

# Missing features
