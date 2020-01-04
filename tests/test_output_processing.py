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


A = [
    Message("z.py", 17, 3, NOTE, "foo"),
    Message("z.py", 18, 3, NOTE, "diff-a"),
    Message("z.py", 20, 1, NOTE, "foo"),
    Message("z.py", 23, 3, NOTE, "unexpected"),
]
B = [
    Message("z.py", 17, 3, NOTE, "foo"),
    Message("z.py", 18, 3, NOTE, "diff-b"),
    Message("z.py", 20, 1, NOTE, "foo"),
    Message("z.py", 25, 3, NOTE, "missing"),
]


def test_output_mismatch_neither_actual_nor_expected():
    with pytest.raises(ValueError):
        OutputMismatch()


def test_output_mismatch_line_number_mismatch():
    msg_a = Message("z.py", 1, 0, NOTE, "foo")
    msg_b = Message("z.py", 2, 0, NOTE, "foo")

    with pytest.raises(ValueError):
        OutputMismatch(msg_a, msg_b)


def test_output_mismatch_with_actual_and_expected():
    actual = Message("z.py", 17, 3, NOTE, "bar")
    expected = Message("z.py", 17, 3, NOTE, "foo")

    om = OutputMismatch(actual=actual, expected=expected)

    assert om.lineno == actual.lineno == expected.lineno
    assert "note" in om.error_message
    assert om.lines


def test_output_mismatch_only_expected():
    expected = Message("z.py", 17, 3, NOTE, "foo")

    om = OutputMismatch(expected=expected)

    assert om.lineno == expected.lineno
    assert "note" in om.error_message
    assert "missing" in om.error_message
    assert not om.lines


def test_output_mismatch_only_actual():
    actual = Message("z.py", 17, 3, NOTE, "foo")

    om = OutputMismatch(actual=actual)

    assert om.lineno == actual.lineno
    assert "note" in om.error_message
    assert "unexpected" in om.error_message
    assert not om.lines


def test_iter_diff_sequences():
    expected = [
        ([A[1]], [B[1]]),
        ([A[3]], [B[3]]),
    ]

    diff = list(iter_msg_seq_diff_chunks(A, B))

    assert diff == expected


def test_diff_message_sequences():

    expected = [
        OutputMismatch(A[1], B[1]),
        OutputMismatch(A[3], None),
        OutputMismatch(None, B[3]),
    ]

    actual = diff_message_sequences(A, B)

    assert actual == expected
