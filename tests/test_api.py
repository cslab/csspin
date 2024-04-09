# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import os
import subprocess
import sys

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
    sh,
    writetext,
)


@pytest.fixture
def cfg():
    cli.load_config_tree("tests/none.yaml", cwd=os.getcwd())
    return get_tree()


def test_interpolate_env():
    assert interpolate1("'{SPIN_CACHE}'") == f"'{os.environ['SPIN_CACHE']}'"


def test_interpolate_n():
    assert interpolate(("a", "b", "c")) == ["a", "b", "c"]


def test_interpolate_recursion(cfg):
    cfg.bad = config()
    cfg.bad.a = "{bad.b}"
    cfg.bad.b = "{bad.a}"
    with pytest.raises(RecursionError):
        interpolate1("{bad.a}")


def test_interpolate_onestep_recursion(cfg):
    cfg.bad = "{bad}"
    assert interpolate1("{bad}") == "{bad}"


def test_interpolate_path():
    p = Path("{SPIN_CACHE}")
    assert isinstance(interpolate1(p), Path)


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
    with cd(tmpdir):
        assert os.getcwd() == tmpdir


def test_mkdir_rmdir(tmpdir):
    xxx = tmpdir + "/xxx"
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
