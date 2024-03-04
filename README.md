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
* `# F: <msg>` - we expect a mypy fatal error message
* `# R: <msg>` - we expect a mypy note message `Revealed type is
  '<msg>'`. This is useful to easily check `reveal_type` output:

     ```python
     @pytest.mark.mypy_testing
     def mypy_use_reveal_type():
         reveal_type(123)  # N: Revealed type is 'Literal[123]?'
         reveal_type(456)  # R: Literal[456]?
     ```

* `# O: <msg>` - we expect a mypy error message and additionally suppress any
  notes on the same line. This is useful to test for errors such as
  `call-overload` where mypy provides extra details in notes along with the error.

## mypy Error Code Matching

The algorithm matching messages parses mypy error code both in the
output generated by mypy and in the Python comments.

If both the mypy output and the Python comment contain an error code
and a full message, then the messages and the error codes must
match. The following test case expects that mypy writes out an
``assignment`` error code and a specific error message:

``` python
@pytest.mark.mypy_testing
def mypy_test_invalid_assignment() -> None:
    foo = "abc"
    foo = 123  # E: Incompatible types in assignment (expression has type "int", variable has type "str")  [assignment]
```

If the Python comment does not contain an error code, then the error
code written out by mypy (if any) is ignored. The following test case
expects a specific error message from mypy, but ignores the error code
produced by mypy:

``` python
@pytest.mark.mypy_testing
def mypy_test_invalid_assignment() -> None:
    foo = "abc"
    foo = 123  # E: Incompatible types in assignment (expression has type "int", variable has type "str")
```

If the Python comment specifies only an error code, then the message
written out by mypy is ignored, i.e., the following test case checks
that mypy reports an `assignment` error:

``` python
@pytest.mark.mypy_testing
def mypy_test_invalid_assignment() -> None:
    foo = "abc"
    foo = 123  # E: [assignment]
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
  Python 3.7, 3.8, 3.9, 3.10, 3.11 and 3.12 must be available. You
  might want to look into using
  [pyenv](https://github.com/pyenv/pyenv).


# Changelog

## Unreleased

## v0.1.3 (2024-03-05)

* Replace usage of deprecated path argument to pytest hook
  ``pytest_collect_file()`` with usage of the file_path argument
  introduced in pytest 7 ([#51][i51], [#52][p52])

## v0.1.2 (2024-02-26)

* Add support for pytest 8 (no actual change, but declare support)
  ([#46][i46], [#47][p47])
* Declare support for Python 3.12 ([#50][p50])
* Update GitHub actions ([#48][p48])
* Update development dependencies ([#49][p49])
* In GitHub PRs run tests with Python 3.11 and 3.12 ([#50][p50])

## v0.1.1

* Compare just mypy error codes if given and no error message is given
  in the test case Python comment ([#36][i36], [#43][p43])

## v0.1.0

* Implement support for flexible matching of mypy error codes (towards
  [#36][i36], [#41][p41])
* Add support for pytest 7.2.x ([#42][p42])
* Add support for mypy 1.0.x ([#42][p42])
* Add support for Python 3.11 ([#42][p42])
* Drop support for pytest 6.x ([#42][p42])
* Drop support for mypy versions less than 0.931 ([#42][p42])

## v0.0.12

* Allow Windows drives in filename ([#17][i17], [#34][p34])
* Support async def tests ([#30][i30], [#31][p31])
* Add support for mypy 0.971 ([#35][i35], [#27][i27])
* Remove support for Python 3.6 ([#32][p32])
* Bump development dependencies ([#40][p40])

## v0.0.11

* Add support for mypy 0.960 ([#25][p25])

## v0.0.10

* Add support for pytest 7.0.x and require Python >= 3.7 ([#23][p23])
* Bump dependencies ([#24][p24])

## v0.0.9

* Disable soft error limit ([#21][p21])

## v0.0.8

* Normalize messages to enable support for mypy 0.902 and pytest 6.2.4 ([#20][p20])

## v0.0.7

* Fix `PYTEST_VERSION_INFO` - by [@blueyed](https://github.com/blueyed) ([#8][p8])
* Always pass `--check-untyped-defs` to mypy ([#11][p11])
* Respect pytest config `python_files` when identifying pytest test modules ([#12][p12])

## v0.0.6 - add pytest 5.4 support

* Update the plugin to work with pytest 5.4 ([#7][p7])

## v0.0.5 - CI improvements

* Make invoke tasks work (partially) on Windows ([#6][p6])
* Add an invoke task to run tox environments by selecting globs (e.g.,
  `inv tox -e py-*`) ([#6][p6])
* Use coverage directly for code coverage to get more consistent
  parallel run results ([#6][p6])
* Use flit fork dflit to make packaging work with `LICENSES` directory
  ([#6][p6])
* Bump dependencies ([#6][p6])


[i17]: https://github.com/davidfritzsche/pytest-mypy-testing/issues/17
[i27]: https://github.com/davidfritzsche/pytest-mypy-testing/issues/27
[i30]: https://github.com/davidfritzsche/pytest-mypy-testing/issues/30
[i35]: https://github.com/davidfritzsche/pytest-mypy-testing/issues/35
[i36]: https://github.com/davidfritzsche/pytest-mypy-testing/issues/36
[i46]: https://github.com/davidfritzsche/pytest-mypy-testing/issues/46
[i51]: https://github.com/davidfritzsche/pytest-mypy-testing/issues/51

[p6]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/6
[p7]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/7
[p8]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/8
[p11]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/11
[p12]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/12
[p20]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/20
[p21]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/21
[p23]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/23
[p24]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/24
[p25]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/25
[p31]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/31
[p32]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/32
[p34]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/34
[p40]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/40
[p41]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/41
[p42]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/42
[p43]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/43
[p47]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/47
[p48]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/48
[p49]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/49
[p50]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/50
[p52]: https://github.com/davidfritzsche/pytest-mypy-testing/pull/52
