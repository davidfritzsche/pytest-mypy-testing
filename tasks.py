import os

from invoke import task


@task
def pth(ctx):
    import distutils.sysconfig

    site_packages_dir = distutils.sysconfig.get_python_lib()
    pth_filename = os.path.join(site_packages_dir, "subprojects.pth")
    with open(pth_filename, "w", encoding="utf-8") as f:
        print(os.path.abspath("src"), file=f)


@task
def mypy(ctx):
    ctx.run("mypy src tests", echo=True, pty=True)


@task
def flake8(ctx):
    ctx.run("flake8", echo=True, pty=True)


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
    ctx.run(" ".join(cmd), echo=True, pty=True)


@task
def black(ctx):
    ctx.run("black --check --diff .", echo=True, pty=True)


@task
def black_reformat(ctx):
    ctx.run("black .", echo=True, pty=True)


@task
def lock_requirements(ctx, upgrade=False):
    cmd = "pip-compile --allow-unsafe --no-index"
    if upgrade:
        cmd += " --upgrade"
    ctx.run(cmd, env={"CUSTOM_COMPILE_COMMAND": cmd}, echo=True, pty=True)


@task
def build(ctx):
    result = ctx.run("git show -s --format=%ct HEAD")
    timestamp = result.stdout.strip()
    cmd = "flit build"
    ctx.run(cmd, env={"SOURCE_DATE_EPOCH": timestamp}, echo=True, pty=True)


@task
def publish(ctx, repository="testpypi"):
    cmd = "flit publish --repository=%s" % (repository,)
    ctx.run(cmd, echo=True, pty=True)


@task(pre=[mypy, pytest, flake8, black])
def check(ctx):
    pass
