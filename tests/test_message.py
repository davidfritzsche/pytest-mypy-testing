# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

import pytest

from pytest_mypy_testing.message import Message, Severity


@pytest.mark.parametrize(
    "string,expected", [("r", Severity.NOTE), ("N", Severity.NOTE)]
)
def test_init_severity(string: str, expected: Severity):
    assert Severity.from_string(string) == expected


@pytest.mark.parametrize(
    "filename,comment,severity,message",
    [
        ("z.py", "# E: bar", Severity.ERROR, "bar"),
        ("z.py", "#type:ignore# W: bar", Severity.WARNING, "bar"),
        ("z.py", "# type: ignore # W: bar", Severity.WARNING, "bar"),
        ("z.py", "# R: bar", Severity.NOTE, "Revealed type is 'bar'"),
    ],
)
def test_message_from_comment(
    filename: str, comment: str, severity: Severity, message: str
):
    lineno = 123
    expected = Message(
        filename=filename,
        lineno=lineno,
        colno=None,
        severity=severity,
        message=message,
    )
    assert Message.from_comment(filename, lineno, comment) == expected


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
