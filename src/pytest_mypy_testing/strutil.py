# SPDX-FileCopyrightText: 2020 David Fritzsche
# SPDX-License-Identifier: Apache-2.0 OR MIT

import textwrap


def common_prefix(a: str, b: str) -> str:
    """Determine the common prefix of *a* and *b*."""
    if len(a) > len(b):
        a, b = b, a
    for i in range(len(a)):
        if a[i] != b[i]:
            return a[:i]
    return a


def dedent(a: str) -> str:
    return textwrap.dedent(a).lstrip("\n")
