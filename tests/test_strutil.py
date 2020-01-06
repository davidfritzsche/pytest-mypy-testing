# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

import pytest

from pytest_mypy_testing.strutil import common_prefix, dedent


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("", "", ""),
        ("a", "a", "a"),
        ("abc", "abcd", "abc"),
        ("abcd", "abc", "abc"),
        ("abc", "xyz", ""),
    ],
)
def test_common_prefix(a: str, b: str, expected: str):
    actual = common_prefix(a, b)
    assert actual == expected


def test_dedent():
    input = """
    foo
    bar
        baz
    """

    expected = "foo\nbar\n    baz\n"
    actual = dedent(input)
    assert actual == expected
