import re

import pytest

from spin import backtick, cli


@pytest.fixture(autouse=True)
def cfg():
    cli.load_config_tree(None)


def do_test(tmpdir, what, cmd):
    output = backtick(
        f"spin -C tests/integration --env {tmpdir} -f {what} --provision {cmd}"
    )
    output = output.strip()
    print(output)
    return output


@pytest.mark.slow
def test_python(tmpdir):
    assert do_test(
        tmpdir,
        "python.yaml",
        "python --version",
    ).endswith("Python 3.9.6")


@pytest.mark.slow
def test_cppcheck(tmpdir):
    out = do_test(
        tmpdir,
        "cppcheck.yaml",
        "python -c \"import shutil; print(shutil.which('cppcheck'))\"",
    )
    assert re.match(r".*cppcheck(.exe)?$", out, re.IGNORECASE)


@pytest.mark.slow
def test_cpplint(tmpdir):
    out = do_test(
        tmpdir,
        "cpplint.yaml",
        "python -c \"import shutil; print(shutil.which('cpplint'))\"",
    )
    assert re.match(r".*cpplint(.exe)?$", out, re.IGNORECASE)


@pytest.mark.slow
def test_flake(tmpdir):
    out = do_test(
        tmpdir,
        "flake.yaml",
        "python -c \"import shutil; print(shutil.which('flake8'))\"",
    )
    assert re.match(r".*flake8(.exe)?$", out, re.IGNORECASE)


@pytest.mark.slow
def test_buildout(tmpdir):
    out = do_test(
        tmpdir,
        "buildout.yaml",
        "python -c \"import shutil; print(shutil.which('buildout'))\"",
    )
    assert re.match(r".*buildout(.exe)?$", out, re.IGNORECASE)


@pytest.mark.slow
def test_build(tmpdir):
    assert "all build tasks" in do_test(
        tmpdir,
        "build.yaml",
        "build --help",
    )
