# SPDX-FileCopyrightText: 2020 David Fritzsche
# SPDX-License-Identifier: Apache-2.0 OR MIT

import os
import tempfile
from typing import Iterable, Iterator, List, NamedTuple, Optional, Tuple

import mypy.api
import pytest
from _pytest._code.code import ReprEntry, ReprFileLocation
from _pytest.config import Config
from py._path.local import LocalPath

from .message import Message, Severity
from .output_processing import OutputMismatch, diff_message_sequences
from .parser import MypyTestItem, parse_file


PYTEST_VERSION = pytest.__version__
PYTEST_VERSION_INFO = tuple(int(part) for part in PYTEST_VERSION.split(".")[:3])


class MypyResult(NamedTuple):
    mypy_args: List[str]
    returncode: int
    output_lines: List[str]
    file_messages: List[Message]
    non_item_messages: List[Message]


class MypyAssertionError(AssertionError):
    def __init__(self, item, errors: Iterable[OutputMismatch]):
        super().__init__(item, errors)
        self.item = item
        self.errors = errors


class PytestMypyTestItem(pytest.Item):
    def __init__(
        self,
        name: str,
        parent: "PytestMypyFile",
        *,
        mypy_item: MypyTestItem,
        config: Optional[Config] = None,
    ) -> None:
        if config is None:
            config = parent.config
        super().__init__(name, parent=parent, config=config)
        self.add_marker("mypy")
        self.mypy_item = mypy_item
        for mark in self.mypy_item.marks:
            self.add_marker(mark)

    @classmethod
    def from_parent(cls, parent, name, mypy_item):
        if PYTEST_VERSION_INFO < (5, 4):
            return cls(
                parent=parent, name=name, config=parent.config, mypy_item=mypy_item
            )
        else:
            return super().from_parent(parent=parent, name=name, mypy_item=mypy_item)

    def runtest(self) -> None:
        returncode, actual_messages = self.parent.run_mypy(self.mypy_item)

        errors = diff_message_sequences(
            actual_messages, self.mypy_item.expected_messages
        )

        if errors:
            raise MypyAssertionError(item=self, errors=errors)

    def reportinfo(self) -> Tuple[str, Optional[int], str]:
        return self.parent.fspath, self.mypy_item.lineno, self.name

    def repr_failure(self, excinfo, style=None):
        if not excinfo.errisinstance(MypyAssertionError):
            return super().repr_failure(excinfo, style=style)  # pragma: no cover
        reprfileloc_key = (
            "filelocrepr" if PYTEST_VERSION_INFO < (5, 4) else "reprfileloc"
        )
        exception_repr = excinfo.getrepr(style="short")
        exception_repr.reprcrash.message = ""
        exception_repr.reprtraceback.reprentries = [
            ReprEntry(
                lines=mismatch.lines,
                style="short",
                reprlocals=None,
                reprfuncargs=None,
                **{
                    reprfileloc_key: ReprFileLocation(
                        path=self.parent.fspath,
                        lineno=mismatch.lineno,
                        message=mismatch.error_message,
                    )
                },
            )
            for mismatch in excinfo.value.errors
        ]
        return exception_repr


class PytestMypyFile(pytest.File):
    def __init__(
        self, fspath: LocalPath, parent=None, config=None, session=None, nodeid=None
    ) -> None:
        if config is None:
            config = getattr(parent, "config", None)
        super().__init__(fspath, parent, config, session, nodeid)
        self.add_marker("mypy")
        self.mypy_file = parse_file(self.fspath, config=config)
        self._mypy_result: Optional[MypyResult] = None

    @classmethod
    def from_parent(cls, parent, fspath):
        if PYTEST_VERSION_INFO < (5, 4):
            config = getattr(parent, "config", None)
            return cls(parent=parent, config=config, fspath=fspath)
        else:
            return super().from_parent(parent=parent, fspath=fspath)

    def collect(self) -> Iterator[PytestMypyTestItem]:
        for item in self.mypy_file.items:
            yield PytestMypyTestItem.from_parent(
                parent=self, name="[mypy]" + item.name, mypy_item=item
            )

    def run_mypy(self, item: MypyTestItem) -> Tuple[int, List[Message]]:
        if self._mypy_result is None:
            self._mypy_result = self._run_mypy(self.fspath)
        return (
            self._mypy_result.returncode,
            sorted(
                item.actual_messages + self._mypy_result.non_item_messages,
                key=lambda msg: msg.lineno,
            ),
        )

    def _run_mypy(self, filename: str) -> MypyResult:
        with tempfile.TemporaryDirectory(prefix="pytest-mypy-testing-") as tmp_dir_name:

            mypy_cache_dir = os.path.join(tmp_dir_name, "mypy_cache")
            os.makedirs(mypy_cache_dir)

            mypy_args = [
                "--cache-dir={}".format(mypy_cache_dir),
                "--check-untyped-defs",
                "--hide-error-context",
                "--no-color-output",
                "--no-error-summary",
                "--no-pretty",
                "--no-silence-site-packages",
                "--no-warn-unused-configs",
                "--show-column-numbers",
                "--show-traceback",
                str(filename),
            ]

            out, err, returncode = mypy.api.run(mypy_args)

        lines = (out + err).splitlines()

        # for line in lines:
        #     print("%%%%", line)

        file_messages = [
            msg
            for msg in map(Message.from_output, lines)
            if (msg.filename == self.mypy_file.filename)
            and not (
                msg.severity is Severity.NOTE
                and msg.message
                == "See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports"
            )
        ]

        non_item_messages = []

        for msg in file_messages:
            for item in self.mypy_file.items:
                if item.lineno <= msg.lineno <= item.end_lineno:
                    item.actual_messages.append(msg)
                    break
            else:
                non_item_messages.append(msg)

        return MypyResult(
            mypy_args=mypy_args,
            returncode=returncode,
            output_lines=lines,
            file_messages=file_messages,
            non_item_messages=non_item_messages,
        )


def pytest_collect_file(path: LocalPath, parent):
    if path.ext == ".mypy-testing" or _is_pytest_test_file(path, parent):
        file = PytestMypyFile.from_parent(parent=parent, fspath=path)
        if file.mypy_file.items:
            return file
    return None


def _is_pytest_test_file(path: LocalPath, parent):
    """Return `True` if *path* is considered to be a pytest test file."""
    # Based on _pytest/python.py::pytest_collect_file
    fn_patterns = parent.config.getini("python_files") + ["__init__.py"]
    return path.ext == ".py" and (
        parent.session.isinitpath(path) or any(path.fnmatch(pat) for pat in fn_patterns)
    )


def pytest_configure(config):
    """
    Register a custom marker for MypyItems,
    and configure the plugin based on the CLI.
    """
    _add_reveal_type_to_builtins()

    config.addinivalue_line(
        "markers", "mypy_testing: mark functions to be used for mypy testing."
    )
    config.addinivalue_line(
        "markers", "mypy: mark mypy tests. Do not add this marker manually!"
    )


def _add_reveal_type_to_builtins():
    # Add a reveal_type function to the builtins module
    import builtins

    if not hasattr(builtins, "reveal_type"):
        setattr(builtins, "reveal_type", lambda x: x)
