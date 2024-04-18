import os
import subprocess
import sys
from unittest.mock import patch

import click
import pytest

from spin import (
    Path,
    appendtext,
    build_target,
    cd,
    cli,
    config,
    echo,
    exists,
    get_tree,
    info,
    interpolate,
    interpolate1,
    memoizer,
    mkdir,
    readtext,
    rmtree,
    setenv,
    sh,
    writetext,
)


@pytest.fixture
def cfg():
    cli.load_config_tree("tests/none.yaml", cwd=os.getcwd())
    return get_tree()


def test_interpolate_n():
    assert interpolate(("a", "b", "c")) == ["a", "b", "c"]


def test_setenv(cfg):
    """
    Test that ensures that spin.setenv is able to set environment variables
    while resolving values to interpolate as well as those which should not
    interpolated.
    """
    cfg["FOO"] = "foo"

    assert setenv(FOO="bar", BAR="foo") is None
    assert os.getenv("FOO") == "bar"
    assert os.getenv("BAR") == "foo"
    assert setenv(FOO="{FOO}") is None
    assert os.getenv("FOO") == "foo"


@patch.dict(os.environ, {"FOO": "foo"})
def test_interpolate1(cfg):
    """
    spin.interpolate1 is able to resolve variables from different sources while
    respecting the escaping syntax.
    """
    # interpolation against the environment
    assert interpolate1("'{FOO}'") == f"'{os.environ['FOO']}'"

    # ... one step recursion
    cfg.bad = "{bad}"
    assert interpolate1("{bad}") == "{bad}"

    # ... two step recursion
    cfg.foo = "{bar}"
    cfg.bar = "final"
    assert interpolate1("{foo}") == "final"

    # ... using a Path against the configuration tree
    cfg["BAR"] = "bar"
    result = interpolate1(Path("{BAR}"))
    assert isinstance(result, Path)
    assert result == Path("bar")

    # ... while escaping curly braces
    assert interpolate1("{{foo}}") == "{foo}"

    # ... while escaping curly braces and resolving from the ConfigTree
    assert (
        interpolate1('{{"header": {{"language": "en", "cache": "{BAR}"}}}}')
        == '{"header": {"language": "en", "cache": "bar"}}'
    )
    # ... while ensuring to escape closing curly braces right to the left
    assert interpolate1("{{{{{foo}}}}}") == "{{final}}"

    # ... triggering the RecursionError
    cfg.bad = config()
    cfg.bad.a = "{bad.b}"
    cfg.bad.b = "{bad.a}"
    with pytest.raises(RecursionError):
        interpolate1("{bad.a}")

    # ... allowing to pass not path and not string
    assert interpolate1(1234) == "1234"
    assert interpolate1(str) == "<class 'str'>"


def test_echo(cfg, mocker):
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    echo(marker)
    for c in click.echo.call_args_list:
        if marker in c.args[0]:
            return
    assert not "echo didn't echo"


def test_quiet(cfg, mocker):
    mocker.patch("click.echo")
    cfg.quiet = True
    echo("")
    assert not click.echo.called


def test_info(cfg, mocker):
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    info(marker)
    assert not click.echo.called
    cfg.verbose = True
    info(marker)
    for c in click.echo.call_args_list:
        if marker in c.args[0]:
            return
    assert not "verbose did not work as expected"


def test_cd(tmpdir):
    with cd(Path(tmpdir)):
        assert os.getcwd() == tmpdir


def test_mkdir_rmdir(tmpdir):
    xxx = Path(tmpdir + "/xxx")
    mkdir(xxx)
    assert exists(xxx)
    rmtree(xxx)
    assert not exists(xxx)


def test_sh(cfg, mocker):
    mocker.patch("subprocess.run")
    sh("abc", "123")
    assert subprocess.run.call_args.args[0] == ["abc", "123"]
    sh("abc 123")
    if sys.platform == "win32":
        assert subprocess.run.call_args.args[0] == ["abc", "123"]

    env = {"_OJDS": "x"}
    sh("abc", "123", env=env)
    assert "env" in subprocess.run.call_args.kwargs
    assert "_OJDS" in subprocess.run.call_args.kwargs["env"]


def test_memoizer(tmpdir):
    memo = f"{tmpdir}/memo"
    with memoizer(memo) as m:
        assert not m.check("abc")
        m.add("abc")
    with memoizer(memo) as m:
        assert m.check("abc")
        assert m.items() == ["abc"]
        m.clear()
    with memoizer(memo) as m:
        assert len(m.items()) == 0


def test_text_files(tmpdir):
    txtf = f"{tmpdir}/x"
    with open(txtf, "w") as f:
        f.write("hello, world")
    assert readtext(txtf) == "hello, world"
    writetext(txtf, "quantum tunnel")
    with open(txtf, "r") as f:
        assert f.read() == "quantum tunnel"
    appendtext(txtf, "ling")
    with open(txtf, "r") as f:
        assert f.read() == "quantum tunnelling"


def test_build_target(cfg, mocker):
    mocker.patch("subprocess.run")
    cfg["build-rules"] = config(
        phony=config(sources="notphony"), notphony=config(script=["1", "2"])
    )
    # According to the rule above, building "phony" would require
    # "notphony" to exist, which would be produced by calling 1 and 2.
    build_target(cfg, "phony", True)
    assert [c.args[0][0] for c in subprocess.run.call_args_list] == ["1", "2"]
