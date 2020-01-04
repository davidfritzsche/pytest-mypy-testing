import pytest

from pytest_mypy_testing.strutil import common_prefix


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
