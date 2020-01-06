# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0


def pytest_cmdline_main(config):
    """Load pytest_mypy_testing if not already present."""
    if not config.pluginmanager.get_plugin("mypy-testing"):
        from pytest_mypy_testing import plugin

        config.pluginmanager.register(plugin)
