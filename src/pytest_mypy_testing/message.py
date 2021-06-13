# SPDX-FileCopyrightText: 2020 David Fritzsche
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Severity and Message"""

import dataclasses
import enum
import os
import re
from typing import Optional, Tuple


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

    TupleType = Tuple[str, int, Optional[int], Severity, str]

    _prefix: str = dataclasses.field(init=False, repr=False, default="")

    COMMENT_RE = re.compile(
        r"^(?:# *type: *ignore *)?(?:# *)?"
        r"(?P<severity>[RENW]):"
        r"((?P<colno>\d+):)? *"
        r"(?P<message>[^#]*)(?:#.*?)?$"
    )

    OUTPUT_RE = re.compile(
        r"^(?P<fname>[^:]+):"
        r"(?P<lineno>[0-9]+):"
        r"((?P<colno>[0-9]+):)?"
        r" *(?P<severity>(error|note|warning)):"
        r"(?P<message>.*)$"
    )

    def astuple(self) -> "Message.TupleType":
        return (
            self.filename,
            self.lineno,
            self.colno,
            self.severity,
            self.message,
        )

    def is_comment(self) -> bool:
        return (self.severity, self.message) in _COMMENT_MESSAGES

    def _as_short_tuple(self, *, normalized: bool = False) -> "Message.TupleType":
        if normalized:
            message = self.message.replace("'", '"')
        else:
            message = self.message
        return (self.filename, self.lineno, None, self.severity, message)

    def __post_init__(self):
        parts = [self.filename, str(self.lineno)]
        if self.colno:
            parts.append(str(self.colno))
        self._prefix = ":".join(parts) + ":"

    def __eq__(self, other):
        if isinstance(other, Message):
            if self.colno is None or other.colno is None:
                return self._as_short_tuple(normalized=True) == other._as_short_tuple(
                    normalized=True
                )
            else:
                return self.astuple() == other.astuple()
        else:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(self._as_short_tuple())

    def __str__(self) -> str:
        return f"{self._prefix} {self.severity.name.lower()}: {self.message}"

    @classmethod
    def from_comment(cls, filename: str, lineno: int, comment: str) -> "Message":
        """Create message object from Python *comment*."""
        m = cls.COMMENT_RE.match(comment.strip())
        if not m:
            raise ValueError("Not a valid mypy message comment")
        colno = int(m.group("colno")) if m.group("colno") else None
        message = m.group("message").strip()
        if m.group("severity") == "R":
            message = "Revealed type is {!r}".format(message)
        return Message(
            filename,
            lineno=lineno,
            colno=colno,
            severity=Severity.from_string(m.group("severity")),
            message=message,
        )

    @classmethod
    def from_output(cls, line: str) -> "Message":
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
