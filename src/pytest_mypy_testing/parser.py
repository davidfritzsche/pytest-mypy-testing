# SPDX-FileCopyrightText: 2020 David Fritzsche
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Parse a Python file to determine the mypy test cases."""

import ast
import dataclasses
import io
import itertools
import os
import pathlib
import sys
import tokenize
from typing import Iterable, Iterator, List, Optional, Set, Tuple, Union

from .message import Message


__all__ = ["parse_file"]


@dataclasses.dataclass
class MypyTestItem:
    name: str
    lineno: int
    end_lineno: int
    expected_messages: List[Message]
    func_node: Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]] = None
    marks: Set[str] = dataclasses.field(default_factory=lambda: set())
    actual_messages: List[Message] = dataclasses.field(default_factory=lambda: [])

    @classmethod
    def from_ast_node(
        cls,
        func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        marks: Optional[Set[str]] = None,
        unfiltered_messages: Optional[Iterable[Message]] = None,
    ) -> "MypyTestItem":
        if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise ValueError(
                f"Invalid func_node type: Got {type(func_node)}, "
                f"expected {ast.FunctionDef} or {ast.AsyncFunctionDef}"
            )
        lineno = func_node.lineno
        end_lineno = getattr(func_node, "end_lineno", 0)

        for node in func_node.decorator_list:
            lineno = min(lineno, node.lineno)

        if unfiltered_messages is not None:
            expected_messages = [
                msg for msg in unfiltered_messages if lineno <= msg.lineno <= end_lineno
            ]
        else:
            expected_messages = []

        return cls(
            name=func_node.name,
            lineno=lineno,
            end_lineno=end_lineno,
            expected_messages=expected_messages,
            func_node=func_node,
            marks=(marks or set()),
        )


@dataclasses.dataclass
class MypyTestFile:
    filename: str
    source_lines: List[str] = dataclasses.field(default_factory=lambda: [])
    items: List[MypyTestItem] = dataclasses.field(default_factory=lambda: [])
    messages: List[Message] = dataclasses.field(default_factory=lambda: [])


def iter_comments(
    filename: Union[pathlib.Path, str], token_lists: List[List[tokenize.TokenInfo]]
) -> Iterator[tokenize.TokenInfo]:
    for toks in token_lists:
        for tok in toks:
            if tok.type == tokenize.COMMENT:
                yield tok


def iter_mypy_comments(
    filename: Union[pathlib.Path, str], tokens: List[List[tokenize.TokenInfo]]
) -> Iterator[Message]:
    for tok in iter_comments(filename, tokens):
        try:
            yield Message.from_comment(filename, tok.start[0], tok.string)
        except ValueError:
            pass


def generate_per_line_token_lists(source: str) -> Iterator[List[tokenize.TokenInfo]]:
    i = 0
    for lineno, group in itertools.groupby(
        tokenize.generate_tokens(io.StringIO(source).readline),
        lambda tok: tok.start[0],
    ):
        assert 0 <= lineno <= 10000000
        while i < lineno:
            yield []
            i += 1
        yield list(group)
        i += 1


def parse_file(filename: Union[os.PathLike, str, pathlib.Path], config) -> MypyTestFile:
    """Parse *filename* and return information about mypy test cases."""
    filename = pathlib.Path(filename).resolve()
    with open(filename, "r", encoding="utf-8") as f:
        source_text = f.read()

    source_lines = source_text.splitlines()
    token_lists = list(generate_per_line_token_lists(source_text))
    messages = list(iter_mypy_comments(filename, token_lists))

    tree = ast.parse(source_text, filename=str(filename))
    if sys.version_info < (3, 8):
        _add_end_lineno_if_missing(tree, len(source_lines))

    items: List[MypyTestItem] = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        marks = _find_marks(node)
        if "mypy_testing" in marks:
            items.append(
                MypyTestItem.from_ast_node(
                    node, marks=marks, unfiltered_messages=messages
                )
            )

    return MypyTestFile(
        filename=str(filename),
        source_lines=source_lines,
        items=items,
        messages=messages,
    )


def _add_end_lineno_if_missing(tree, line_count: int):
    """Add end_lineno attribute to top-level nodes if missing"""
    prev_node: Optional[ast.AST] = None
    for node in ast.iter_child_nodes(tree):
        if prev_node is not None:
            setattr(prev_node, "end_lineno", getattr(node, "lineno", 0))  # noqa: B010
        prev_node = node
    if prev_node:
        setattr(prev_node, "end_lineno", line_count)  # noqa: B010


def _find_marks(func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Set[str]:
    return {
        name.split(".", 2)[2]
        for name, _ in _iter_func_decorators(func_node)
        if name.startswith("pytest.mark.")
    }


def _iter_func_decorators(
    func_node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
) -> Iterator[Tuple[str, ast.AST]]:
    def dotted(*nodes):
        return ".".join(_get_node_name(node) for node in reversed(nodes))

    for decorator_node in func_node.decorator_list:
        if isinstance(decorator_node, (ast.Name, ast.Attribute)):
            node, attrs = _unwrap_ast_attributes(decorator_node)
            if isinstance(node, ast.Name):
                yield dotted(*attrs, node), decorator_node

        elif isinstance(decorator_node, ast.Call):
            node, attrs = _unwrap_ast_attributes(decorator_node.func)
            if isinstance(node, ast.Name):
                yield dotted(*attrs, node), decorator_node


def _get_node_name(node) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr
    elif isinstance(node, ast.Name):
        return node.id
    else:
        raise RuntimeError(f"Unsupported node type: {type(node)}")  # pragma: no cover


def _unwrap_ast_attributes(node) -> Tuple[ast.AST, List[ast.Attribute]]:
    attrs: List[ast.Attribute] = []
    while isinstance(node, ast.Attribute):
        attrs.append(node)
        node = node.value
    return node, attrs
