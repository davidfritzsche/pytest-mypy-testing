import os
import tempfile
from typing import Iterable, Iterator, List, NamedTuple, Optional, Tuple

import mypy.api
import pytest
from _pytest._code.code import ReprEntry, ReprFileLocation
from _pytest.config import Config
from py._path.local import LocalPath

from .message import Message
from .output_processing import OutputMismatch, diff_message_sequences
from .parser import MypyTestItem, parse_file


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
        config: Config,
        mypy_item: MypyTestItem,
    ) -> None:
        super().__init__(name, parent, config)
        self.add_marker("mypy")
        self.mypy_item = mypy_item
        for mark in self.mypy_item.marks:
            self.add_marker(mark)

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
        if excinfo.errisinstance(MypyAssertionError):
            exception_repr = excinfo.getrepr(style="short")
            exception_repr.reprcrash.message = ""
            exception_repr.reprtraceback.reprentries = [
                ReprEntry(
                    filelocrepr=ReprFileLocation(
                        path=self.parent.fspath,
                        lineno=mismatch.lineno,
                        message=mismatch.error_message,
                    ),
                    lines=mismatch.lines,
                    style="short",
                    reprlocals=None,
                    reprfuncargs=None,
                )
                for mismatch in excinfo.value.errors
            ]
            return exception_repr
        else:
            return super().repr_failure(excinfo, style=style)  # pragma: no cover


class PytestMypyFile(pytest.File):
    def __init__(
        self, fspath: LocalPath, parent=None, config=None, session=None, nodeid=None,
    ) -> None:
        super().__init__(fspath, parent, config, session, nodeid)
        self.add_marker("mypy")
        self.mypy_file = parse_file(self.fspath)
        self._mypy_result: Optional[MypyResult] = None

    def collect(self) -> Iterator[PytestMypyTestItem]:
        for item in self.mypy_file.items:
            yield PytestMypyTestItem(
                name="[mypy]" + item.name,
                parent=self,
                config=self.config,
                mypy_item=item,
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
                "--show-traceback",
                "--show-column-numbers",
                "--no-silence-site-packages",
                "--no-error-summary",
                "--no-pretty",
                "--hide-error-context",
                "--cache-dir={}".format(mypy_cache_dir),
                str(filename),
            ]

            out, err, returncode = mypy.api.run(mypy_args)

        lines = (out + err).splitlines()
        file_messages = [
            msg
            for msg in map(Message.from_output, lines)
            if msg.filename == self.mypy_file.filename
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
    import builtins

    # Add a reveal_type function to the builtins module
    if not hasattr(builtins, "reveal_type"):
        setattr(builtins, "reveal_type", lambda x: x)

    config = getattr(parent, "config", None)

    if path.ext in (".mypy-testing", ".py") and path.basename.startswith("test_"):
        file = PytestMypyFile(path, parent=parent, config=config)
        if file.mypy_file.items:
            return file
    else:
        return None  # pragma: no cover


def pytest_configure(config):
    """
    Register a custom marker for MypyItems,
    and configure the plugin based on the CLI.
    """
    config.addinivalue_line(
        "markers", "mypy_testing: mark functions to be used for mypy testing."
    )
    config.addinivalue_line(
        "markers", "mypy: mark mypy tests. Do not add this marker manually!"
    )
