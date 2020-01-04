from types import SimpleNamespace

from py._path.local import LocalPath

from pytest_mypy_testing.message import Severity
from pytest_mypy_testing.parser import MypyTestFile
from pytest_mypy_testing.plugin import (
    MypyAssertionError,
    PytestMypyFile,
    pytest_collect_file,
)


ERROR = Severity.ERROR
NOTE = Severity.NOTE
WARNING = Severity.WARNING


def test_create_mypy_assertion_error():
    MypyAssertionError(None, [])


def mk_dummy_parent(tmp_path, filename):

    path = tmp_path / filename
    path.write_text("")

    config = SimpleNamespace(rootdir=str(tmp_path))
    session = SimpleNamespace(config=config, _initialpaths=[])
    parent = SimpleNamespace(
        config=config,
        session=session,
        nodeid="dummy",
        fspath=LocalPath(path),
        _path=path,
    )

    return parent


def test_pytest_collect_file_not_test_file_name(tmp_path):
    parent = mk_dummy_parent(tmp_path, "z.py")

    assert pytest_collect_file(parent.fspath, parent) is None


def test_pytest_collect_file(tmp_path):
    parent = mk_dummy_parent(tmp_path, "test_z.mypy")
    expected = MypyTestFile(filename=str(parent._path))

    actual = pytest_collect_file(parent.fspath, parent)
    assert isinstance(actual, PytestMypyFile)

    assert actual.mypy_file == expected
