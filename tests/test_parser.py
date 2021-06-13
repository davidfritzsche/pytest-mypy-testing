# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

import ast
import sys
from tokenize import COMMENT, ENDMARKER, NAME, NEWLINE, NL, TokenInfo
from unittest.mock import Mock

import pytest
from _pytest.config import Config

from pytest_mypy_testing.parser import (
    MypyTestItem,
    generate_per_line_token_lists,
    parse_file,
)
from pytest_mypy_testing.strutil import dedent


@pytest.mark.parametrize("node", [None, 123, "abc"])
def test_cannot_create_mypy_test_case_from_ast_node_without_valid_node(node):
    with pytest.raises(ValueError):
        MypyTestItem.from_ast_node(node)


def test_create_mypy_test_case():
    func = dedent(
        r"""
        @pytest.mark.mypy_testing
        @pytest.mark.skip()
        @foo.bar
        def mypy_foo():
            pass
        """
    )
    tree = ast.parse(func, "func.py")

    func_nodes = [
        node for node in ast.iter_child_nodes(tree) if isinstance(node, ast.FunctionDef)
    ]

    assert func_nodes

    tc = MypyTestItem.from_ast_node(func_nodes[0])

    assert tc.lineno == 1


def test_iter_comments():
    source = "\n".join(["# foo", "assert True # E: bar"])

    actual = list(generate_per_line_token_lists(source))

    # fmt: off
    expected = [
        [],  # line 0
        [
            TokenInfo(type=COMMENT, string="# foo", start=(1, 0), end=(1, 5), line="# foo\n",),
            TokenInfo(type=NL, string="\n", start=(1, 5), end=(1, 6), line="# foo\n"),
        ],
        [
            TokenInfo(type=NAME, string="assert", start=(2, 0), end=(2, 6), line="assert True # E: bar",),
            TokenInfo(type=NAME, string="True", start=(2, 7), end=(2, 11), line="assert True # E: bar",),
            TokenInfo(type=COMMENT, string="# E: bar", start=(2, 12), end=(2, 20), line="assert True # E: bar",),
            TokenInfo(type=NEWLINE, string="", start=(2, 20), end=(2, 21), line=""),
        ],
        [
            TokenInfo(type=ENDMARKER, string="", start=(3, 0), end=(3, 0), line="")
        ],
    ]
    # fmt: on

    assert actual == expected


def test_parse_file_basic_call_works_with_py37(monkeypatch, tmp_path):
    path = tmp_path / "parse_file_test.py"
    path.write_text(
        dedent(
            r"""
            # foo
            def test_mypy_foo():
                pass
            @pytest.mark.mypy_testing
            def test_mypy_bar():
                pass
            """
        )
    )

    monkeypatch.setattr(sys, "version_info", (3, 7, 5))
    config = Mock(spec=Config)
    parse_file(str(path), config)
