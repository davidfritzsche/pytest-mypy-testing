# SPDX-FileCopyrightText: David Fritzsche
# SPDX-License-Identifier: CC0-1.0

import os
import sys

from invoke import task


MAYBE_PTY = sys.platform != "win32"


@task
def mkdir(ctx, dirname):
    os.makedirs(dirname, exist_ok=True)


@task
def pth(ctx):
    import distutils.sysconfig

    site_packages_dir = distutils.sysconfig.get_python_lib()
    pth_filename = os.path.join(site_packages_dir, "subprojects.pth")
    with open(pth_filename, "w", encoding="utf-8") as f:
        print(os.path.abspath("src"), file=f)


@task(pre=[pth])
def tox(ctx, parallel="auto", e="ALL"):
    import fnmatch
    import itertools

    env_patterns = list(filter(None, e.split(",")))
    result = ctx.run("tox --listenvs-all", hide=True, pty=False)
    all_envs = result.stdout.splitlines()

    if any(pat == "ALL" for pat in env_patterns):
        envs = set(all_envs)
    else:
        envs = set(
            itertools.chain.from_iterable(
                fnmatch.filter(all_envs, pat) for pat in env_patterns
            )
        )
    envlist = ",".join(sorted(envs))
    ctx.run(f"tox --parallel={parallel} -e {envlist}", echo=True, pty=MAYBE_PTY)


@task
def mypy(ctx):
    ctx.run("mypy src tests", echo=True, pty=MAYBE_PTY)


@task
def flake8(ctx):
    ctx.run("flake8", echo=True, pty=MAYBE_PTY)


@task(pre=[pth])
def pytest(ctx):
    cmd = [
        "pytest",
        # "-s",
        # "--log-cli-level=DEBUG",
        "--cov=pytest_mypy_testing",
        "--cov-report=html:build/cov_html",
        "--cov-report=term:skip-covered",
    ]
    ctx.run(" ".join(cmd), echo=True, pty=MAYBE_PTY)


@task
def black(ctx):
    ctx.run("black --check --diff .", echo=True, pty=MAYBE_PTY)


@task
def reuse_lint(ctx):
    ctx.run("reuse lint", echo=True, pty=MAYBE_PTY)


@task
def black_reformat(ctx):
    ctx.run("black .", echo=True, pty=MAYBE_PTY)


@task
def lock_requirements(ctx, upgrade=False):
    cmd = "pip-compile --allow-unsafe --no-index"
    if upgrade:
        cmd += " --upgrade"
    ctx.run(cmd, env={"CUSTOM_COMPILE_COMMAND": cmd}, echo=True, pty=MAYBE_PTY)


@task
def build(ctx):
    result = ctx.run("git show -s --format=%ct HEAD")
    timestamp = result.stdout.strip()
    cmd = "flit build"
    ctx.run(cmd, env={"SOURCE_DATE_EPOCH": timestamp}, echo=True, pty=MAYBE_PTY)


@task
def publish(ctx, repository="testpypi"):
    cmd = "flit publish --repository=%s" % (repository,)
    ctx.run(cmd, echo=True, pty=MAYBE_PTY)


@task(pre=[mypy, pytest, flake8])
def check(ctx):
    pass
