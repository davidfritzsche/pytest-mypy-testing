# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

from typing import List, Tuple

import pytest

from pytest_mypy_testing.message import Message, Severity
from pytest_mypy_testing.output_processing import (
    OutputMismatch,
    diff_message_sequences,
    iter_msg_seq_diff_chunks,
)


ERROR = Severity.ERROR
NOTE = Severity.NOTE
WARNING = Severity.WARNING


MSGS_DIFF_A_SINGLE = [Message("z.py", 15, 1, NOTE, "diff-a")]
MSGS_DIFF_B_SINGLE = [Message("z.py", 15, 1, NOTE, "diff-b")]

MSGS_DIFF_A_MULTI = [
    Message("z.py", 25, 1, NOTE, "diff-a"),
    Message("z.py", 25, 1, NOTE, "diff-a error"),
]
MSGS_DIFF_B_MULTI = [Message("z.py", 25, 1, NOTE, "diff-b")]

MSGS_UNEXPECTED_A_SINGLE = [
    Message("z.py", 35, 1, NOTE, "unexpected"),
]

MSGS_UNEXPECTED_A_MULTI = [
    Message("z.py", 45, 1, NOTE, "unexpected"),
    Message("z.py", 45, 1, ERROR, "unexpected error"),
]

MSGS_MISSING_B_SINGLE = [
    Message("z.py", 55, 1, NOTE, "missing"),
]

MSGS_MISSING_B_MULTI = [
    Message("z.py", 65, 1, ERROR, "missing error"),
    Message("z.py", 65, 1, NOTE, "missing note"),
]

A = [
    Message("z.py", 10, 3, ERROR, "equal error"),
    Message("z.py", 10, 3, NOTE, "equal"),
    *MSGS_DIFF_A_SINGLE,
    Message("z.py", 20, 1, NOTE, "equal"),
    *MSGS_DIFF_A_MULTI,
    Message("z.py", 30, 1, NOTE, "equal"),
    *MSGS_UNEXPECTED_A_SINGLE,
    Message("z.py", 40, 1, NOTE, "equal"),
    *MSGS_UNEXPECTED_A_MULTI,
    Message("z.py", 50, 1, NOTE, "equal"),
    Message("z.py", 60, 1, NOTE, "equal"),
    Message("z.py", 70, 1, NOTE, "equal"),
]
B = [
    Message("z.py", 10, 3, ERROR, "equal error"),
    Message("z.py", 10, 3, NOTE, "equal"),
    *MSGS_DIFF_B_SINGLE,
    Message("z.py", 20, 1, NOTE, "equal"),
    *MSGS_DIFF_B_MULTI,
    Message("z.py", 30, 1, NOTE, "equal"),
    Message("z.py", 40, 1, NOTE, "equal"),
    Message("z.py", 50, 1, NOTE, "equal"),
    *MSGS_MISSING_B_SINGLE,
    Message("z.py", 60, 1, NOTE, "equal"),
    *MSGS_MISSING_B_MULTI,
    Message("z.py", 70, 1, NOTE, "equal"),
]

EXPECTED_DIFF_SEQUENCE: List[Tuple[List[Message], List[Message]]] = [
    (MSGS_DIFF_A_SINGLE, MSGS_DIFF_B_SINGLE),
    (MSGS_DIFF_A_MULTI, MSGS_DIFF_B_MULTI),
    (MSGS_UNEXPECTED_A_SINGLE, []),
    (MSGS_UNEXPECTED_A_MULTI, []),
    ([], MSGS_MISSING_B_SINGLE),
    ([], MSGS_MISSING_B_MULTI),
]


def test_output_mismatch_neither_actual_nor_expected():
    with pytest.raises(ValueError):
        OutputMismatch()


def test_output_mismatch_actual_lineno_or_severity_without_actual():
    msg = Message("z.py", 1, 0, NOTE, "foo")
    om = OutputMismatch(expected=[msg])

    with pytest.raises(RuntimeError):
        om.actual_lineno
    with pytest.raises(RuntimeError):
        om.actual_severity


def test_output_mismatch_expected_lineno_or_severity_without_expected():
    msg = Message("z.py", 1, 0, NOTE, "foo")
    om = OutputMismatch(actual=[msg])

    with pytest.raises(RuntimeError):
        om.expected_lineno
    with pytest.raises(RuntimeError):
        om.expected_severity


def test_output_mismatch_line_number_mismatch():
    msg_a = Message("z.py", 1, 0, NOTE, "foo")
    msg_b = Message("z.py", 2, 0, NOTE, "foo")

    with pytest.raises(ValueError):
        OutputMismatch([msg_a], [msg_b])


def test_output_mismatch_with_actual_and_expected():
    actual = Message("z.py", 17, 3, NOTE, "bar")
    expected = Message("z.py", 17, 3, NOTE, "foo")

    om = OutputMismatch(actual=[actual], expected=[expected])

    assert om.lineno == actual.lineno == expected.lineno
    assert "note" in om.error_message
    assert om.lines


def test_output_mismatch_only_expected():
    expected = Message("z.py", 17, 3, NOTE, "foo")

    om = OutputMismatch(expected=[expected])

    assert om.lineno == expected.lineno
    assert "note" in om.error_message
    assert "missing" in om.error_message
    assert not om.lines


def test_output_mismatch_only_actual():
    actual = Message("z.py", 17, 3, NOTE, "foo")

    om = OutputMismatch(actual=[actual])

    assert om.lineno == actual.lineno
    assert "note" in om.error_message
    assert "unexpected" in om.error_message
    assert not om.lines


def test_iter_diff_sequences():
    diff = list(iter_msg_seq_diff_chunks(A, B))

    assert diff == EXPECTED_DIFF_SEQUENCE


def test_diff_message_sequences():
    expected = [OutputMismatch(a, e) for a, e in EXPECTED_DIFF_SEQUENCE]

    actual = diff_message_sequences(A, B)

    assert actual == expected
