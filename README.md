![GitHub Action Status](https://github.com/davidfritzsche/pytest-mypy-testing/workflows/Python%20package/badge.svg)


# pytest-mypy-testing — Plugin to test mypy output with pytest

`pytest-mypy-testing` provides a
[pytest](https://pytest.readthedocs.io/en/latest/) plugin to test that
[mypy](http://mypy-lang.org/) produces a given output. As mypy can be
told to [display the type of an
expression](https://mypy.readthedocs.io/en/latest/common_issues.html#displaying-the-type-of-an-expression)
this allows us to check mypys type interference.


# Installation

``` shell
pip install pytest-mypy-testing
```

The Python distribution package contains an [entry
point](https://docs.pytest.org/en/latest/writing_plugins.html#making-your-plugin-installable-by-others)
so that the plugin is automatically discovered by pytest. To disable
the plugin when it is installed , you can use the pytest command line
option `-p no:mypy-testing`.


# Writing Mypy Output Test Cases

A mypy test case is a top-level functions decorated with
`@pytest.mark.mypy_testing` in a file name `test_*.py` or
`test_*.mypy-testing`.  Note that we use the Python
[ast](https://docs.python.org/3/library/ast.html) module to parse
candidate files and do not import any file, i.e., the decorator must
be exactly named `@pytest.mark.mypy_testing`.

In a `test_*.py` file you may combine both regular pytest test
functions and mypy test functions. A single function can even be both.

Example: A simple mypy test case could look like this:

``` python
@pytest.mark.mypy_testing
def mypy_test_invalid_assginment():
    foo = "abc"
    foo = 123  # E: Incompatible types in assignment (expression has type "int", variable has type "str")
```

The plugin runs mypy for every file containing at least one mypy test
case. The mypy output is then compared to special Python comments in
the file:

* `# N: <msg>` - we expect a mypy note message
* `# W: <msg>` - we expect a mypy warning message
* `# E: <msg>` - we expect a mypy error message
* `# R: <msg>` - we expect a mypy note message `Revealed type is
  '<msg>'`. This is useful to easily check `reveal_type` output:
     ```python
     @pytest.mark.mypy_testing
     def mypy_use_reveal_type():
         reveal_type(123)  # N: Revealed type is 'Literal[123]?'
         reveal_type(456)  # R: Literal[456]?
     ```


## Skipping and Expected Failures

Mypy test case functions can be decorated with `@pytest.mark.skip` and
`@pytest.mark.xfail` to mark them as to-be-skipped and as
expected-to-fail, respectively. As with the
`@pytest.mark.mypy_testing` mark, the names must match exactly as the
decorators are extracted from the ast.


# Development

* Create and activate a Python virtual environment.
* Install development dependencies by calling `pip install -U -r requirements.txt`.
* Start developing
* To run all tests with [tox](https://tox.readthedocs.io/en/latest/),
  Python 3.6, 3.7 and 3.8 must be available. You might want to look
  into using [pyenv](https://github.com/pyenv/pyenv).
