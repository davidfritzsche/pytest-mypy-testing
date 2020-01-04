import dataclasses
import difflib
from typing import Iterator, List, Optional, Sequence, Tuple

from .message import Message
from .strutil import common_prefix


@dataclasses.dataclass
class OutputMismatch:
    actual: Optional[Message] = None
    expected: Optional[Message] = None
    lineno: int = dataclasses.field(init=False, default=0)
    lines: List[str] = dataclasses.field(init=False, default_factory=lambda: [])
    error_message: str = dataclasses.field(init=False, default="")

    def __post_init__(self) -> None:
        if not any([self.actual, self.expected]):
            raise ValueError("At least one of actual and expected must be given")

        if self.actual:
            self.lineno = self.actual.lineno
        elif self.expected:
            self.lineno = self.expected.lineno

        if self.actual and self.expected:
            if self.actual.lineno != self.expected.lineno:
                raise ValueError("line numbers do not match")
            self.lineno = self.actual.lineno
            self.error_message = f"{self.actual.severity} (mismatch):"
            sp = " " * len(common_prefix(self.actual.message, self.expected.message))
            self.lines = [
                f"  A: {self.actual.severity.name[0]}: {self.actual.message}",
                f"  E: {self.expected.severity.name[0]}: {self.expected.message}",
                f"        {sp}^",
            ]
        elif self.actual:
            self.lineno = self.actual.lineno
            self.error_message = (
                f"{self.actual.severity} (unexpected): {self.actual.message}"
            )
            self.lines = []
        else:
            assert self.expected
            self.lineno = self.expected.lineno
            self.error_message = (
                f"{self.expected.severity} (missing): {self.expected.message}"
            )
            self.lines = []


def diff_message_sequences(
    actual_messages: Sequence[Message], expected_messages: Sequence[Message]
) -> List[OutputMismatch]:
    """Diff lists of messages"""

    errors: List[OutputMismatch] = []

    for a_chunk, b_chunk in iter_msg_seq_diff_chunks(
        actual_messages, expected_messages
    ):
        a_dict = {msg.lineno: msg for msg in a_chunk}
        b_dict = {msg.lineno: msg for msg in b_chunk}

        linenos_set = set(a_dict.keys()) | set(b_dict.keys())

        linenos = sorted(linenos_set)

        for lineno in linenos:
            actual = a_dict.get(lineno, None)
            expected = b_dict.get(lineno, None)
            errors.append(OutputMismatch(actual=actual, expected=expected))

    return errors


def iter_msg_seq_diff_chunks(
    a: Sequence[Message], b: Sequence[Message]
) -> Iterator[Tuple[Sequence[Message], Sequence[Message]]]:
    """Iterate over sequences of not matching messages"""
    seq_matcher = difflib.SequenceMatcher(isjunk=None, a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in seq_matcher.get_opcodes():
        if tag != "equal":
            yield a[i1:i2], b[j1:j2]
