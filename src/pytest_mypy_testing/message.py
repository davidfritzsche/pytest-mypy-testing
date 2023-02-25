# SPDX-FileCopyrightText: 2020 David Fritzsche
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Severity and Message"""

import dataclasses
import enum
import os
import pathlib
import re
from typing import Optional, Tuple, Union


__all__ = [
    "Message",
    "Severity",
]


class Severity(enum.Enum):
    """Severity of a mypy message."""

    NOTE = 1
    WARNING = 2
    ERROR = 3

    @classmethod
    def from_string(cls, string: str) -> "Severity":
        return _string_to_severity[string.upper()]

    def __str__(self) -> str:
        return self.name.lower()

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}.{self.name}"


_string_to_severity = {
    "R": Severity.NOTE,
    "N": Severity.NOTE,
    "W": Severity.WARNING,
    "E": Severity.ERROR,
}

_COMMENT_MESSAGES = frozenset(
    [
        (
            Severity.NOTE,
            "See https://mypy.readthedocs.io/en/latest/running_mypy.html#missing-imports",
        ),
    ]
)


@dataclasses.dataclass
class Message:
    """Mypy message"""

    filename: str
    lineno: int
    colno: Optional[int]
    severity: Severity
    message: str
    revealed_type: Optional[str] = None
    error_code: Optional[str] = None

    TupleType = Tuple[
        str, int, Optional[int], Severity, str, Optional[str], Optional[str]
    ]

    _prefix: str = dataclasses.field(init=False, repr=False, default="")

    COMMENT_RE = re.compile(
        r"^(?:# *type: *ignore *)?(?:# *)?"
        r"(?P<severity>[RENW]):"
        r"((?P<colno>\d+):)? *"
        r"(?P<message>[^#]*?)"
        r"(?: +\[(?P<error_code>[^\]]*)\])?"
        r"(?:#.*?)?$"
    )

    OUTPUT_RE = re.compile(
        r"^(?P<fname>([a-zA-Z]:)?[^:]+):"
        r"(?P<lineno>[0-9]+):"
        r"((?P<colno>[0-9]+):)?"
        r" *(?P<severity>(error|note|warning)):"
        r"(?P<message>.*?)"
        r"(?: +\[(?P<error_code>[^\]]*)\])?"
        r"$"
    )

    _OUTPUT_REVEALED_RE = re.compile(
        "^Revealed type is (?P<quoted_type>'[^']+'|\"[^\"]+\")$"
    )

    _INFERRED_TYPE_ASTERISK_RE = re.compile("(?<=[A-Za-z])[*]")

    def __post_init__(self):
        parts = [self.filename, str(self.lineno)]
        if self.colno:
            parts.append(str(self.colno))
        self._prefix = ":".join(parts) + ":"
        if not self.revealed_type:
            revealed_m = self._OUTPUT_REVEALED_RE.match(self.message)
            if revealed_m:
                self.revealed_type = revealed_m.group("quoted_type")[1:-1]
        if self.revealed_type:
            # Remove the '*' for inferred types from reveal_type output.
            # This matches the behavior of mypy 0.950 and newer.
            self.revealed_type = self._INFERRED_TYPE_ASTERISK_RE.sub(
                "", self.revealed_type
            )

    @property
    def normalized_message(self) -> str:
        """Normalized message.

        >>> m = Message("foo.py", 1, 1, Severity.NOTE, 'Revealed type is "float"')
        >>> m.normalized_message
        "Revealed type is 'float'"
        """
        if self.revealed_type:
            return "Revealed type is {!r}".format(self.revealed_type)
        else:
            return self.message.replace("'", '"')

    def astuple(self, *, normalized: bool = False) -> "Message.TupleType":
        """Return a tuple representing this message.

        >>> m = Message("foo.py", 1, 1, Severity.NOTE, 'Revealed type is "float"')
        >>> m.astuple()
        ('foo.py', 1, 1, Severity.NOTE, 'Revealed type is "float"', 'float')
        """
        return (
            self.filename,
            self.lineno,
            self.colno,
            self.severity,
            self.normalized_message if normalized else self.message,
            self.revealed_type,
            self.error_code,
        )

    def is_comment(self) -> bool:
        return (self.severity, self.message) in _COMMENT_MESSAGES

    def _as_short_tuple(
        self, *, normalized: bool = False, default_error_code: Optional[str] = None
    ) -> "Message.TupleType":
        if normalized:
            message = self.normalized_message
        else:
            message = self.message
        return (
            self.filename,
            self.lineno,
            None,
            self.severity,
            message,
            self.revealed_type,
            self.error_code or default_error_code,
        )

    def __eq__(self, other):
        if isinstance(other, Message):
            default_error_code = self.error_code or other.error_code
            if self.colno is None or other.colno is None:
                a = self._as_short_tuple(
                    normalized=True, default_error_code=default_error_code
                )
                b = other._as_short_tuple(
                    normalized=True, default_error_code=default_error_code
                )
                return a == b
            else:
                return self.astuple(normalized=True) == other.astuple(normalized=True)
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self._as_short_tuple(normalized=True))

    def __str__(self) -> str:
        return f"{self._prefix} {self.severity.name.lower()}: {self.message}"

    @classmethod
    def from_comment(
        cls, filename: Union[pathlib.Path, str], lineno: int, comment: str
    ) -> "Message":
        """Create message object from Python *comment*.

        >>> Message.from_comment("foo.py", 1, "R: foo")
        Message(filename='foo.py', lineno=1, colno=None, severity=Severity.NOTE, message="Revealed type is 'foo'", revealed_type='foo')
        """
        m = cls.COMMENT_RE.match(comment.strip())
        if not m:
            raise ValueError("Not a valid mypy message comment")
        colno = int(m.group("colno")) if m.group("colno") else None
        message = m.group("message").strip()
        if m.group("severity") == "R":
            revealed_type = message
            message = "Revealed type is {!r}".format(message)
        else:
            revealed_type = None
        return Message(
            str(filename),
            lineno=lineno,
            colno=colno,
            severity=Severity.from_string(m.group("severity")),
            message=message,
            revealed_type=revealed_type,
            error_code=m.group("error_code") or None,
        )

    @classmethod
    def from_output(cls, line: str) -> "Message":
        """Create message object from mypy output line.

        >>> m = Message.from_output("z.py:1: note: bar")
        >>> (m.lineno, m.colno, m.severity, m.message, m.revealed_type)
        (1, None, Severity.NOTE, 'bar', None)

        >>> m = Message.from_output("z.py:1:13: note: bar")
        >>> (m.lineno, m.colno, m.severity, m.message, m.revealed_type)
        (1, 13, Severity.NOTE, 'bar', None)

        >>> m = Message.from_output("z.py:1: note: Revealed type is 'bar'")
        >>> (m.lineno, m.colno, m.severity, m.message, m.revealed_type)
        (1, None, Severity.NOTE, "Revealed type is 'bar'", 'bar')

        >>> m = Message.from_output('z.py:1: note: Revealed type is "bar"')
        >>> (m.lineno, m.colno, m.severity, m.message, m.revealed_type)
        (1, None, Severity.NOTE, 'Revealed type is "bar"', 'bar')

        """
        m = cls.OUTPUT_RE.match(line)
        if not m:
            raise ValueError("Not a valid mypy message")
        return cls(
            os.path.abspath(m.group("fname")),
            lineno=int(m.group("lineno")),
            colno=int(m.group("colno")) if m.group("colno") else None,
            severity=Severity[m.group("severity").upper()],
            message=m.group("message").strip(),
        )
