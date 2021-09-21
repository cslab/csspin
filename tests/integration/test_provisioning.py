import pytest

from spin import backtick, cli


@pytest.fixture(autouse=True)
def cfg():
    cli.load_config_tree(None)


def do_test(tmpdir, what, cmd):
    output = backtick(
        f"spin -C tests/integration --env {tmpdir} -f {what} --provision {cmd}"
    )
    print(output)
    return output


@pytest.mark.slow
def test_python(tmpdir):
    assert do_test(
        tmpdir,
        "python.yaml",
        "python --version",
    ).endswith("Python 3.9.6\n")


@pytest.mark.slow
def test_cppcheck(tmpdir):
    assert do_test(
        tmpdir,
        "cppcheck.yaml",
        "run which cppcheck",
    ).endswith("cppcheck\n")


@pytest.mark.slow
def test_cpplint(tmpdir):
    assert do_test(
        tmpdir,
        "cpplint.yaml",
        "run which cpplint",
    ).endswith("cpplint\n")


@pytest.mark.slow
def test_flake(tmpdir):
    assert do_test(
        tmpdir,
        "flake.yaml",
        "run which flake8",
    ).endswith("flake8\n")


@pytest.mark.slow
def test_buildout(tmpdir):
    assert do_test(
        tmpdir,
        "buildout.yaml",
        "run which buildout",
    ).endswith("buildout\n")


@pytest.mark.slow
def test_build(tmpdir):
    assert "all build tasks" in do_test(
        tmpdir,
        "build.yaml",
        "build --help",
    )
