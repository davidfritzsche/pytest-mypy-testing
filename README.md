<!--
SPDX-FileCopyrightText: David Fritzsche
SPDX-License-Identifier: CC0-1.0
-->
[![PyPI](https://img.shields.io/pypi/v/pytest-mypy-testing.svg)](https://pypi.python.org/pypi/pytest-mypy-testing)
[![GitHub Action Status](https://github.com/davidfritzsche/pytest-mypy-testing/workflows/Python%20package/badge.svg)](https://github.com/davidfritzsche/pytest-mypy-testing/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


# pytest-mypy-testing — Plugin to test mypy output with pytest

`pytest-mypy-testing` provides a
[pytest](https://pytest.readthedocs.io/en/latest/) plugin to test that
[mypy](http://mypy-lang.org/) produces a given output. As mypy can be
told to [display the type of an
expression](https://mypy.readthedocs.io/en/latest/common_issues.html#displaying-the-type-of-an-expression)
this allows us to check mypys type interference.


# Installation

``` shell
python -m pip install pytest-mypy-testing
```

The Python distribution package contains an [entry
point](https://docs.pytest.org/en/latest/writing_plugins.html#making-your-plugin-installable-by-others)
so that the plugin is automatically discovered by pytest. To disable
the plugin when it is installed , you can use the pytest command line
option `-p no:mypy-testing`.


# Writing Mypy Output Test Cases

A mypy test case is a top-level functions decorated with
`@pytest.mark.mypy_testing` in a file named `*.mypy-testing` or in a
pytest test module.  `pytest-mypy-testing` follows the pytest logic in
identifying test modules and respects the
[`python_files`](https://docs.pytest.org/en/latest/reference.html#confval-python_files)
config value.

Note that ``pytest-mypy-testing`` uses the Python
[ast](https://docs.python.org/3/library/ast.html) module to parse
candidate files and does not import any file, i.e., the decorator must
be exactly named `@pytest.mark.mypy_testing`.

In a pytest test module file you may combine both regular pytest test
functions and mypy test functions. A single function can be both.

Example: A simple mypy test case could look like this:

``` python
@pytest.mark.mypy_testing
def mypy_test_invalid_assignment() -> None:
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
* Install development dependencies by calling `python -m pip install
  -U -r requirements.txt`.
* Start developing.
* To run all tests with [tox](https://tox.readthedocs.io/en/latest/),
  Python 3.7, 3.8, 3.9 and 3.10 must be available. You might want to look
  into using [pyenv](https://github.com/pyenv/pyenv).


# Changelog

## v0.0.10

* Add support for pytest 7.0.x and require Python >= 3.7 (#23)
* Bump dependencies (#24)

## v0.0.9

* Disable soft error limit (#21)

## v0.0.8

* Normalize messages to enable support for mypy 0.902 and pytest 6.2.4 (#20)

## v0.0.7

* Fix `PYTEST_VERSION_INFO` - by [@blueyed](https://github.com/blueyed) (#8)
* Always pass `--check-untyped-defs` to mypy (#11)
* Respect pytest config `python_files` when identifying pytest test modules (#12)

## v0.0.6 - add pytest 5.4 support

* Update the plugin to work with pytest 5.4 (#7)

## v0.0.5 - CI improvements

* Make invoke tasks work (partially) on Windows (#6)
* Add an invoke task to run tox environments by selecting globs (e.g.,
  `inv tox -e py-*`) (#6)
* Use coverage directly for code coverage to get more consistent
  parallel run results (#6)
* Use flit fork dflit to make packaging work with `LICENSES` directory
  (#6)
* Bump dependencies (#6)
