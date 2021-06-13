# SPDX-FileCopyrightText: 2020 David Fritzsche
# SPDX-License-Identifier: Apache-2.0 OR MIT

import dataclasses
import difflib
import itertools
from typing import Dict, Iterator, List, Sequence, Tuple

from .message import Message, Severity
from .strutil import common_prefix


@dataclasses.dataclass
class OutputMismatch:
    actual: List[Message] = dataclasses.field(default_factory=lambda: [])
    expected: List[Message] = dataclasses.field(default_factory=lambda: [])
    lineno: int = dataclasses.field(init=False, default=0)
    lines: List[str] = dataclasses.field(init=False, default_factory=lambda: [])
    error_message: str = dataclasses.field(init=False, default="")

    @property
    def actual_lineno(self) -> int:
        if self.actual:
            return self.actual[0].lineno
        raise RuntimeError("No actual messages")

    @property
    def expected_lineno(self) -> int:
        if self.expected:
            return self.expected[0].lineno
        raise RuntimeError("No expected messages")

    @property
    def actual_severity(self) -> Severity:
        if not self.actual:
            raise RuntimeError("No actual messages")
        return Severity(max(msg.severity.value for msg in self.actual))

    @property
    def expected_severity(self) -> Severity:
        if not self.expected:
            raise RuntimeError("No expected messages")
        return Severity(max(msg.severity.value for msg in self.expected))

    def __post_init__(self) -> None:
        def _fmt(msg: Message, actual_expected: str = "", *, indent: str = "  ") -> str:
            if actual_expected:
                actual_expected += ": "
            return (
                f"{indent}{actual_expected}{msg.severity.name.lower()}: {msg.message}"
            )

        if not any([self.actual, self.expected]):
            raise ValueError("At least one of actual and expected must be given")

        if self.actual:
            self.lineno = self.actual_lineno
        elif self.expected:
            self.lineno = self.expected_lineno

        assert self.lines == []

        if self.actual and self.expected:
            if self.actual_lineno != self.expected_lineno:
                raise ValueError("line numbers do not match")
            self.error_message = f"{self.actual[0].severity} (mismatch):"
            if len(self.actual) == len(self.expected) == 1:
                sp = " " * len(
                    common_prefix(self.actual[0].message, self.expected[0].message)
                )
                sp_lines = [f"        {sp}^"]
            else:
                sp_lines = []
            self.lines = (
                [_fmt(msg, "A") for msg in self.actual]
                + [_fmt(msg, "E") for msg in self.expected]
                + sp_lines
            )
        elif self.actual:
            if len(self.actual) == 1:
                self.error_message = (
                    f"{self.actual_severity} (unexpected): {self.actual[0].message}"
                )
            else:
                self.error_message = f"{self.actual_severity} (unexpected):"
                self.lines = [_fmt(msg, "A") for msg in self.actual]
        else:
            assert self.expected
            if len(self.expected) == 1:
                self.error_message = (
                    f"{self.expected_severity} (missing): {self.expected[0].message}"
                )
            else:
                self.error_message = f"{self.expected_severity} (missing):"
                self.lines = [_fmt(msg, "E") for msg in self.expected]


def diff_message_sequences(
    actual_messages: Sequence[Message], expected_messages: Sequence[Message]
) -> List[OutputMismatch]:
    """Diff lists of messages"""

    def _chunk_to_dict(chunk: Sequence[Message]) -> Dict[int, List[Message]]:
        d: Dict[int, List[Message]] = {}
        for msg in chunk:
            d.setdefault(msg.lineno, []).append(msg)
        return d

    errors: List[OutputMismatch] = []

    for a_chunk, b_chunk in iter_msg_seq_diff_chunks(
        actual_messages, expected_messages
    ):

        a_dict = _chunk_to_dict(a_chunk)
        b_dict = _chunk_to_dict(b_chunk)

        linenos_set = set(a_dict.keys()) | set(b_dict.keys())

        linenos = sorted(linenos_set)

        for lineno in linenos:
            actual = a_dict.get(lineno, [])
            expected = b_dict.get(lineno, [])

            if any((not msg.is_comment()) for msg in itertools.chain(actual, expected)):
                errors.append(OutputMismatch(actual=actual, expected=expected))

    return errors


def iter_msg_seq_diff_chunks(
    a: Sequence[Message], b: Sequence[Message]
) -> Iterator[Tuple[Sequence[Message], Sequence[Message]]]:
    """Iterate over sequences of not matching messages"""
    seq_matcher = difflib.SequenceMatcher(isjunk=None, a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in seq_matcher.get_opcodes():
        if tag == "equal":
            continue
        actual = a[i1:i2]
        expected = b[j1:j2]
        if actual or expected:
            yield actual, expected
