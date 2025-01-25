# SPDX-FileCopyrightText: 2020 David Fritzsche
# SPDX-License-Identifier: Apache-2.0 OR MIT

import os
import pathlib
from typing import Dict, Iterable, Iterator, List, NamedTuple, Optional, Tuple, Union

import mypy.api
import pytest
from _pytest._code.code import ReprEntry, ReprFileLocation
from _pytest.config import Config
from _pytest.python import path_matches_patterns

from .message import Message, Severity
from .output_processing import OutputMismatch, diff_message_sequences
from .parser import MypyTestItem, parse_file


PYTEST_VERSION = pytest.__version__
PYTEST_VERSION_INFO = tuple(int(part) for part in PYTEST_VERSION.split(".")[:3])


class MypyResult(NamedTuple):
    file_messages: List[Message]
    non_item_messages: List[Message]


class MypyAssertionError(AssertionError):
    def __init__(self, item, errors: Iterable[OutputMismatch]):
        super().__init__(item, errors)
        self.item = item
        self.errors = errors


class PytestMypyTestItem(pytest.Item):
    parent: "PytestMypyFile"

    def __init__(
        self,
        name: str,
        parent: "PytestMypyFile",
        *,
        mypy_item: MypyTestItem,
        config: Optional[Config] = None,
        **kwargs,
    ) -> None:
        if config is None:
            config = parent.config
        super().__init__(name, parent=parent, config=config, **kwargs)
        self.add_marker("mypy")
        self.mypy_item = mypy_item
        for mark in self.mypy_item.marks:
            self.add_marker(mark)

    @classmethod
    def from_parent(cls, parent, name, mypy_item):
        return super().from_parent(parent=parent, name=name, mypy_item=mypy_item)

    def runtest(self) -> None:
        actual_messages = self.parent.run_mypy(self.mypy_item)

        errors = diff_message_sequences(
            actual_messages, self.mypy_item.expected_messages
        )

        if errors:
            raise MypyAssertionError(item=self, errors=errors)

    def reportinfo(self) -> Tuple[Union["os.PathLike[str]", str], Optional[int], str]:
        return self.parent.path, self.mypy_item.lineno, self.name

    def repr_failure(self, excinfo, style=None):
        if not excinfo.errisinstance(MypyAssertionError):
            return super().repr_failure(excinfo, style=style)  # pragma: no cover
        reprfileloc_key = "reprfileloc"
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
                        path=str(self.parent.path),
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
        self,
        *,
        parent=None,
        config=None,
        session=None,
        nodeid=None,
        **kwargs,
    ) -> None:
        if config is None:
            config = getattr(parent, "config", None)
        super().__init__(
            parent=parent,
            config=config,
            session=session,
            nodeid=nodeid,
            **kwargs,
        )
        self.add_marker("mypy")
        self.mypy_file = parse_file(self.path, config=config)
        COLLECTION.add(self)

    @classmethod
    def from_parent(cls, parent, **kwargs):
        return super().from_parent(parent=parent, **kwargs)

    def collect(self) -> Iterator[PytestMypyTestItem]:
        for item in self.mypy_file.items:
            yield PytestMypyTestItem.from_parent(
                parent=self, name="[mypy]" + item.name, mypy_item=item
            )

    def run_mypy(self, item: MypyTestItem) -> List[Message]:
        mypy_result = COLLECTION.run_mypy(self)
        return sorted(
            item.actual_messages + mypy_result.non_item_messages,
            key=lambda msg: msg.lineno,
        )


class MypyFileCollection:
    def __init__(self):
        self.files: List[PytestMypyFile] = []
        self._mypy_results: Optional[Dict[str, MypyResult]] = None

    def add(self, file: PytestMypyFile):
        self.files.append(file)

    def run_mypy(self, file: PytestMypyFile) -> MypyResult:
        if self._mypy_results is None:
            self._mypy_results = self._run_mypy()
        return self._mypy_results[str(file.path)]

    def _run_mypy(self) -> Dict[str, MypyResult]:
        mypy_args = [
            "--cache-dir={}".format(self.files[0].config.cache.mkdir("mypy-cache")),
            "--check-untyped-defs",
            "--hide-error-context",
            "--no-color-output",
            "--no-error-summary",
            "--no-pretty",
            "--soft-error-limit=-1",
            "--no-warn-unused-configs",
            "--show-column-numbers",
            "--show-error-codes",
            "--show-traceback",
            *(str(file.path) for file in self.files),
        ]

        out, err, returncode = mypy.api.run(mypy_args)

        messages_by_file = {}

        for line in (out + err).splitlines():
            msg = Message.from_output(line)
            if msg.filename and not (
                msg.severity is Severity.NOTE
                and msg.message.endswith("#missing-imports")
            ):
                messages_by_file.setdefault(msg.filename, []).append(msg)

        ret = {}
        for file in self.files:
            file_messages = messages_by_file.get(str(file.path), [])

            non_item_messages = []

            for msg in file_messages:
                for item in file.mypy_file.items:
                    if item.lineno <= msg.lineno <= item.end_lineno:
                        item.actual_messages.append(msg)
                        break
                else:
                    non_item_messages.append(msg)

            ret[str(file.path)] = MypyResult(
                file_messages=file_messages,
                non_item_messages=non_item_messages,
            )

        return ret


COLLECTION = MypyFileCollection()


def pytest_collect_file(file_path: pathlib.Path, parent):
    if file_path.suffix == ".mypy-testing" or _is_pytest_test_file(file_path, parent):
        file = PytestMypyFile.from_parent(parent=parent, path=file_path)
        if file.mypy_file.items:
            return file
    return None


def _is_pytest_test_file(file_path: pathlib.Path, parent):
    """Return `True` if *path* is considered to be a pytest test file."""
    # Based on _pytest/python.py::pytest_collect_file
    fn_patterns = parent.config.getini("python_files") + ["__init__.py"]
    return file_path.suffix == ".py" and (
        parent.session.isinitpath(file_path)
        or path_matches_patterns(file_path, fn_patterns)
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
        setattr(builtins, "reveal_type", lambda x: x)  # noqa: B010
