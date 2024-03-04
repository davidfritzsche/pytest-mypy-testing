# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

import pathlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from _pytest.config import Config

from pytest_mypy_testing.message import Severity
from pytest_mypy_testing.parser import MypyTestFile
from pytest_mypy_testing.plugin import (
    MypyAssertionError,
    PytestMypyFile,
    pytest_collect_file,
)
from pytest_mypy_testing.strutil import dedent


PYTEST_VERSION = pytest.__version__
PYTEST_VERSION_INFO = tuple(int(part) for part in PYTEST_VERSION.split(".")[:3])


ERROR = Severity.ERROR
NOTE = Severity.NOTE
WARNING = Severity.WARNING


def call_pytest_collect_file(file_path: pathlib.Path, parent):
    return pytest_collect_file(file_path, parent)


def test_create_mypy_assertion_error():
    MypyAssertionError(None, [])


def mk_dummy_parent(tmp_path: pathlib.Path, filename, content=""):
    path = tmp_path / filename
    path.write_text(content)

    config = Mock(spec=Config)
    config.rootdir = str(tmp_path)
    config.rootpath = str(tmp_path)
    config.getini.return_value = ["test_*.py", "*_test.py"]
    session = SimpleNamespace(
        config=config, isinitpath=lambda p: True, _initialpaths=[]
    )
    parent = SimpleNamespace(
        config=config,
        session=session,
        nodeid="dummy",
        path=path,
    )

    return parent


@pytest.mark.parametrize("filename", ["z.py", "test_z.mypy-testing"])
def test_pytest_collect_file_not_test_file_name(tmp_path, filename: str):
    parent = mk_dummy_parent(tmp_path, filename)
    file_path = parent.path
    actual = call_pytest_collect_file(file_path, parent)
    assert actual is None


@pytest.mark.parametrize("filename", ["test_z.py", "test_z.mypy-testing"])
def test_pytest_collect_file(tmp_path, filename):
    content = dedent(
        """
        @pytest.mark.mypy_testing
        def foo():
            pass
        """
    )

    parent = mk_dummy_parent(tmp_path, filename, content)
    expected = MypyTestFile(
        filename=str(parent.path), source_lines=content.splitlines()
    )

    file_path = parent.path
    actual = call_pytest_collect_file(file_path, parent)
    assert isinstance(actual, PytestMypyFile)

    assert len(actual.mypy_file.items) == 1
    actual.mypy_file.items = []

    assert actual.mypy_file == expected
