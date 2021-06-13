# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from _pytest.config import Config
from py._path.local import LocalPath

from pytest_mypy_testing.message import Severity
from pytest_mypy_testing.parser import MypyTestFile
from pytest_mypy_testing.plugin import (
    MypyAssertionError,
    PytestMypyFile,
    pytest_collect_file,
)
from pytest_mypy_testing.strutil import dedent


ERROR = Severity.ERROR
NOTE = Severity.NOTE
WARNING = Severity.WARNING


def test_create_mypy_assertion_error():
    MypyAssertionError(None, [])


def mk_dummy_parent(tmp_path, filename, content=""):

    path = tmp_path / filename
    path.write_text(content)

    config = Mock(spec=Config)
    config.rootdir = str(tmp_path)
    config.getini.return_value = ["test_*.py", "*_test.py"]
    session = SimpleNamespace(
        config=config, isinitpath=lambda p: True, _initialpaths=[]
    )
    parent = SimpleNamespace(
        config=config,
        session=session,
        nodeid="dummy",
        fspath=LocalPath(path),
        _path=path,
    )

    return parent


@pytest.mark.parametrize("filename", ["z.py", "test_z.mypy-testing"])
def test_pytest_collect_file_not_test_file_name(tmp_path, filename: str):
    parent = mk_dummy_parent(tmp_path, filename)

    assert pytest_collect_file(parent.fspath, parent) is None


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
        filename=str(parent._path), source_lines=content.splitlines()
    )

    actual = pytest_collect_file(parent.fspath, parent)
    assert isinstance(actual, PytestMypyFile)

    assert len(actual.mypy_file.items) == 1
    actual.mypy_file.items = []

    assert actual.mypy_file == expected
