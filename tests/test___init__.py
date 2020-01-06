# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

import re

from pytest_mypy_testing.__init__ import __version__


def test_version():
    assert re.match("^[0-9]*([.][0-9]*)*$", __version__)
