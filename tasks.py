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
def tox(ctx, e="ALL"):
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
    ctx.run(f"tox -e {envlist}", echo=True, pty=MAYBE_PTY)


@task
def mypy(ctx):
    ctx.run("mypy", echo=True, pty=MAYBE_PTY)


@task
def ruff(ctx):
    ctx.run("ruff check .", echo=True, pty=MAYBE_PTY)


@task
def ruff_format(ctx):
    ctx.run("ruff format --check .", echo=True, pty=MAYBE_PTY)


@task
def ruff_reformat(ctx):
    ctx.run("ruff format .", echo=True, pty=MAYBE_PTY)


@task
def reuse_lint(ctx):
    ctx.run("reuse lint", echo=True, pty=MAYBE_PTY)


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


@task(pre=[mypy, ruff, ruff_format, reuse_lint])
def check(ctx):
    pass
