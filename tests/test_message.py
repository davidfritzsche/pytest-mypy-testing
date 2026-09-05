# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

from typing import Optional

import pytest

from pytest_mypy_testing.message import Message, Severity


@pytest.mark.parametrize(
    "string,expected", [("r", Severity.NOTE), ("N", Severity.NOTE)]
)
def test_init_severity(string: str, expected: Severity):
    assert Severity.from_string(string) == expected


@pytest.mark.parametrize(
    "filename,comment,severity,message,error_code",
    [
        ("z.py", "# E: bar", Severity.ERROR, "bar", None),
        ("z.py", "# E: bar", Severity.ERROR, "bar", "foo"),
        ("z.py", "# E: bar [foo]", Severity.ERROR, "bar", "foo"),
        ("z.py", "# E: bar [foo]", Severity.ERROR, "bar", ""),
        ("z.py", "#type:ignore# W: bar", Severity.WARNING, "bar", None),
        ("z.py", "# type: ignore # W: bar", Severity.WARNING, "bar", None),
        ("z.py", "# R: bar", Severity.NOTE, "Revealed type is 'bar'", None),
    ],
)
def test_message_from_comment(
    filename: str,
    comment: str,
    severity: Severity,
    message: str,
    error_code: Optional[str],
):
    lineno = 123
    actual = Message.from_comment(filename, lineno, comment)
    expected = Message(
        filename=filename,
        lineno=lineno,
        colno=None,
        severity=severity,
        message=message,
        error_code=error_code,
    )
    assert actual == expected


def test_message_from_invalid_comment():
    with pytest.raises(ValueError):
        Message.from_comment("foo.py", 1, "# fubar")


@pytest.mark.parametrize(
    "line,severity,message",
    [
        ("z.py:1: note: bar", Severity.NOTE, "bar"),
        ("z.py:1:2: note: bar", Severity.NOTE, "bar"),
        ("z.py:1:2: error: fubar", Severity.ERROR, "fubar"),
    ],
)
def test_message_from_output(line: str, severity: Severity, message: str):
    msg = Message.from_output(line)
    assert msg.message == message
    assert msg.severity == severity


@pytest.mark.parametrize(
    "output",
    [
        "foo.py:a: fubar",
        "fubar",
        "foo.py:1: fubar",
        "foo.py:1:1: fubar",
        "foo.py:1:1: not: fubar",
    ],
)
def test_message_from_invalid_output(output):
    with pytest.raises(ValueError):
        Message.from_output(output)


MSG_WITHOUT_COL = Message("z.py", 13, None, Severity.NOTE, "foo")
MSG_WITH_COL = Message("z.py", 13, 23, Severity.NOTE, "foo")


@pytest.mark.parametrize(
    "a,b",
    [
        (MSG_WITH_COL, MSG_WITH_COL),
        (MSG_WITH_COL, MSG_WITHOUT_COL),
        (MSG_WITHOUT_COL, MSG_WITHOUT_COL),
        (MSG_WITHOUT_COL, MSG_WITH_COL),
    ],
)
def test_message_eq(a: Message, b: Message):
    assert a == b
    assert not (a != b)


def test_message_neq_with_not_message():
    assert MSG_WITH_COL != 23
    assert MSG_WITH_COL != "abc"


def test_message_hash():
    assert hash(MSG_WITH_COL) == hash(MSG_WITHOUT_COL)


def test_message_str():
    assert str(MSG_WITHOUT_COL) == "z.py:13: note: foo"
    assert str(MSG_WITH_COL) == "z.py:13:23: note: foo"


@pytest.mark.parametrize(
    "expected_comment,actual_message",
    [
        ("# R: builtins.int", 'Revealed type is "int"'),
        ("# R: int", 'Revealed type is "builtins.int"'),
        ("# R: builtins.list[builtins.int]", 'Revealed type is "list[int]"'),
        ("# R: list[int]", 'Revealed type is "builtins.list[builtins.int]"'),
        ("# R: builtins.float", "Revealed type is 'float'"),
    ],
)
def test_reveal_type_equates_builtins_prefix(
    expected_comment: str, actual_message: str
):
    """mypy 1.20 dropped the builtins. prefix from reveal_type notes.

    Expected comments written for older mypy (R: builtins.int) must still
    match actual notes that omit the prefix (Revealed type is "int"), and
    the reverse must also match.
    """
    expected = Message.from_comment("z.py", 1, expected_comment)
    actual = Message("z.py", 1, None, Severity.NOTE, actual_message)
    assert expected == actual
    assert actual == expected
    assert hash(expected) == hash(actual)


def test_reveal_type_builtins_prefix_does_not_equate_different_types():
    expected = Message.from_comment("z.py", 1, "# R: builtins.int")
    actual = Message("z.py", 1, None, Severity.NOTE, 'Revealed type is "str"')
    assert expected != actual
