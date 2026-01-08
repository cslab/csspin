# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""
Module implementing the unit tests regarding the API functions and classes
implemented in src/spin/__init__.py
"""

from __future__ import annotations

import os
import pickle
import subprocess
import sys
from pathlib import Path as PathlibPath
from typing import TYPE_CHECKING, Callable
from unittest import mock
from unittest.mock import patch

import click
import pytest
from path import Path

import csspin
from csspin import Verbosity
from csspin.tree import ConfigTree

if TYPE_CHECKING:

    from typing import Any

    from pytest_mock.plugin import MockerFixture


def test_echo(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """csspin.echo is echo'ing when CONFIG.verbosity is not QUIET"""
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    csspin.echo(marker)
    for call in click.echo.call_args_list:  # type: ignore[attr-defined]
        assert any(
            expected in call.args[0] for expected in ("spin: ", marker)
        ), f"None of the expected values found in {call.args[0]=}"


def test_echo_quiet(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """csspin.echo is not echo'ing if CONFIG.verbosity is QUIET"""
    mocker.patch("click.echo")
    cfg.verbosity = Verbosity.QUIET
    csspin.echo("Should not be shown")
    assert not click.echo.called  # type: ignore[attr-defined]


def test_info_quiet(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """csspin.info is not info'ing if CONFIG.verbosity < INFO"""
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    csspin.info(marker)
    assert not click.echo.called  # type: ignore[attr-defined]


def test_info_verbose(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """csspin.info is info'ing if CONFIG.verbosity is set to INFO"""
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    cfg.verbosity = Verbosity.INFO
    csspin.info(marker)
    for call in click.echo.call_args_list:  # type: ignore[attr-defined]
        assert any(
            expected in call.args[0] for expected in ("spin: ", marker)
        ), f"None of the expected values found in {call.args[0]=}"


def test_debug_quiet(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """csspin.debug is not debugging if CONFIG.verbosity < DEBUG"""
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    cfg.verbosity = Verbosity.INFO
    csspin.debug(marker)
    assert not click.echo.called  # type: ignore[attr-defined]


def test_debug(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """csspin.debug is not debugging if CONFIG.verbosity < DEBUG"""
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    cfg.verbosity = Verbosity.DEBUG
    csspin.debug(marker)
    for call in click.echo.call_args_list:  # type: ignore[attr-defined]
        assert any(
            expected in call.args[0] for expected in ("spin: ", marker)
        ), f"None of the expected values found in {call.args[0]=}"


@pytest.mark.parametrize(
    "function,message",
    ((csspin.warn, "warning"), (csspin.error, "error")),
)
def test_echo_extended(function: Callable, message: str, mocker: MockerFixture) -> None:
    f"""csspin.{message} gets called using the expected arguments."""  # pylint: disable=pointless-statement
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    function(marker)
    for call in click.echo.call_args_list:  # type: ignore[attr-defined]
        assert any(
            expected in call.args[0] for expected in (f"spin: {message}", marker)
        ), f"None of the expected values found in {call.args[0]=}"


def test_directory_changer(
    tmp_path: PathlibPath,
    cfg: ConfigTree,
    mocker: MockerFixture,
) -> None:
    """csspin.DirectoryChanger is able to change directories accordingly"""
    cwd = os.getcwd()
    mock_echo = mocker.patch("click.echo")

    with csspin.DirectoryChanger(path=tmp_path):
        assert os.getcwd() == str(tmp_path)
        assert str(tmp_path) in repr(click.echo.call_args_list).replace("\\\\", "\\")  # type: ignore[attr-defined] # noqa: E501
    assert os.getcwd() == cwd
    assert cwd in repr(click.echo.call_args_list).replace("\\\\", "\\")  # type: ignore[attr-defined]

    mock_echo.reset_mock()

    # if nothing to do, directory changer does nothing and echoes nothing
    with csspin.DirectoryChanger(path=cwd):
        assert os.getcwd() == cwd
        assert cwd not in repr(click.echo.call_args_list).replace("\\\\", "\\")  # type: ignore[attr-defined]


def test_cd(cfg, tmp_path: PathlibPath) -> None:
    """csspin.cd is changing the current directory as expected"""
    cwd = os.getcwd()
    with csspin.cd(tmp_path):
        assert os.getcwd() == str(tmp_path)
    assert cwd == os.getcwd()


def test_exists(cfg: ConfigTree, tmp_path: PathlibPath) -> None:
    """csspin.exists is able to validate the existence of directories"""
    cfg["TMPDIR"] = tmp_path
    assert os.path.isdir(tmp_path)
    assert csspin.exists("{TMPDIR}")
    assert csspin.exists(tmp_path)
    assert not csspin.exists(r"\foo/bar\baz/biz\buz")


def test_normpath(cfg: ConfigTree) -> None:
    """
    csspin.normpath is resolving environment variables to return the normalized
    path
    """
    cfg["FOO"] = "foo"
    assert csspin.normpath("{FOO}") == os.path.normpath("foo")


def test_abspath(cfg: ConfigTree) -> None:
    """
    csspin.abspath is resolving environment variables to return the absolute path
    """
    cfg["FOO"] = "foo"
    assert csspin.abspath("{FOO}") == os.path.abspath("foo")


def test_mkdir(tmp_path: PathlibPath) -> None:
    """
    csspin.mkdir is able to create directories and will not fail if the directory
    already exists
    """
    csspin.mkdir(tmp_path)
    path = tmp_path / "foo"
    csspin.mkdir(path)
    assert os.path.isdir(path)


def test_mkdir_rmtree(tmp_path: PathlibPath) -> None:
    """csspin.rmtree is able to delete directories"""
    xxx = tmp_path / "xxx"
    assert not csspin.exists(xxx)
    csspin.mkdir(xxx)
    assert csspin.exists(xxx)
    csspin.rmtree(xxx)
    assert not csspin.exists(xxx)


def test_rmtree_file(tmp_path: PathlibPath) -> None:
    """csspin.rmtree is able to delete files"""
    tmp_file = tmp_path / "tempfile"
    tmp_file.touch()

    assert csspin.exists(tmp_file)
    csspin.rmtree(tmp_file)
    assert not csspin.exists(tmp_file)


def test_mv(tmp_path: PathlibPath) -> None:
    """csspin.mv is able to move and rename files and directories"""
    from tempfile import mktemp

    with pytest.raises(click.Abort, match=".* does not exist!"):
        csspin.mv(mktemp(), tmp_path)

    subdir_a = tmp_path / "sub_a"
    subdir_b = tmp_path / "sub_b"
    subdir_a.mkdir()
    subdir_b.mkdir()
    file_ = subdir_a / "file.txt"
    file_.write_text("")

    # move file
    csspin.mv(file_, subdir_b)
    assert (subdir_b / "file.txt").is_file()
    assert not file_.is_file()

    # move directory
    csspin.mv(subdir_b, subdir_a)
    assert ((file_path := subdir_a / "sub_b" / "file.txt")).is_file()
    assert not subdir_b.is_dir()

    # rename file
    csspin.mv(file_path, (new_file_path := subdir_a / "sub_b" / "file2.txt"))
    assert not file_path.is_file()
    assert new_file_path.is_file()


def test_copy(tmp_path: PathlibPath) -> None:
    """csspin.copy is able to copy files and directories to the desired
    locations
    """
    source_dir = tmp_path / "directory"
    source_dir.mkdir()
    file_ = source_dir / "file.txt"
    file_.write_text("foo")
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # copy file
    csspin.copy(file_, target_dir)
    assert file_.is_file()
    assert (target_dir / "file.txt").is_file()

    # copy directory
    csspin.copy(source_dir, target_dir)
    assert (target_dir / "directory" / "file.txt").is_file()


def test_die() -> None:
    """csspin.die will raise click.Abort"""
    with pytest.raises(click.Abort, match="You shall not pass!"):
        csspin.die("You shall not pass!")


def test_command() -> None:
    """
    csspin.command will instantiate the csspin.Command class which is able to call
    its basic functions
    """
    # pylint: disable=protected-access
    cmd = csspin.Command("pip", "list")
    assert cmd._cmd == ["pip", "list"]

    cmd.append("--help")
    assert cmd._cmd == ["pip", "list", "--help"]


def test_sh(cfg, mocker: MockerFixture) -> None:
    """
    csspin.sh will raise the expected errors on faulty input as well as execute
    valid commands by calling subprocess.run with the correct arguments
    """
    # check=True, shell=False
    with pytest.raises(
        click.Abort,
        match=(
            ".*WinError 2.*"
            if sys.platform == "win32"
            else ".*No such file or directory.*FileNotFoundTrigger.*"
        ),
    ):
        csspin.sh("FileNotFoundTrigger", shell=False)

    # check=False, shell=False
    with pytest.raises(
        click.Abort,
        match=(
            ".*WinError 2.*"
            if sys.platform == "win32"
            else ".*No such file or directory.*FileNotFoundTrigger.*"
        ),
    ):
        csspin.sh("FileNotFoundTrigger", shell=False, check=False)

    # check=True, shell=True
    with pytest.raises(
        click.Abort,
        match=".*Command.*'spin foobar'.*failed with exit status.*",
    ):
        csspin.sh("spin", "foobar")

    # check=False, shell=True
    with mock.patch("csspin.warn") as spin_warn:
        csspin.sh("spin", "foobar", check=False)
        assert (
            "Command '['spin', 'foobar']' failed with exit status"
            in spin_warn.call_args.args[0]
        )

    mocker.patch("subprocess.run")
    csspin.sh("abc", "123 4")
    assert subprocess.run.call_args.args[0] == ["abc", "123 4"]  # type: ignore[attr-defined]

    env = {"_OJDS": "x"}
    csspin.sh("abc", "123", env=env)
    assert "env" in subprocess.run.call_args.kwargs  # type: ignore[attr-defined]
    assert "_OJDS" in subprocess.run.call_args.kwargs["env"]  # type: ignore[attr-defined]


def test_backtick(mocker: MockerFixture) -> None:
    """
    csspin.backtick is calling csspin.sh using the correct arguments and returning
    the expected value
    """
    from socket import gethostname

    assert csspin.backtick("hostname") == f"{gethostname()}{os.linesep}"

    mocker.patch("csspin.sh")
    csspin.backtick("hostname")
    csspin.sh.assert_called_with("hostname", stdout=-1)


def test__read_file(minimum_yaml_path: str) -> None:
    """csspin._read_file reads from file and returns the content"""
    # pylint: disable=protected-access
    expected = "foo: bar\n"
    assert csspin._read_file(fn=minimum_yaml_path, mode="r") == expected

    with mock.patch.dict(os.environ, {"TEST_MINIMUM_YAML_PATH": minimum_yaml_path}):
        assert csspin._read_file(fn="{TEST_MINIMUM_YAML_PATH}", mode="r") == expected


def test__read_lines(minimum_yaml_path: str) -> None:
    """csspin._read_lines is able to read and return multiple lines from a file"""
    # pylint: disable=protected-access
    expected = ["foo: bar\n"]
    assert csspin.readlines(fn=minimum_yaml_path) == expected
    with mock.patch.dict(os.environ, {"TEST_MINIMUM_YAML_PATH": minimum_yaml_path}):
        assert csspin.readlines(fn="{TEST_MINIMUM_YAML_PATH}") == expected


def test_writelines(tmp_path: PathlibPath) -> None:
    """csspin.writelines writes multiple lines into a file"""
    content = "foo:\n  - bar\n  - baz"
    expected = ["foo:\n", "  - bar\n", "  - baz"]
    assert csspin.writelines(fn=tmp_path / "test.txt", lines=content) is None
    with open(tmp_path / "test.txt", "r", encoding="utf-8") as f:
        assert f.readlines() == expected


def test_write_file(tmp_path: PathlibPath) -> None:
    """csspin.write_file writes a string to file"""
    # pylint: disable=protected-access
    ofile = tmp_path / "test.txt"
    content = "Lone line"
    csspin._write_file(ofile, mode="w", data=content)
    assert os.path.isfile(ofile)
    with open(ofile, "r", encoding="UTF-8") as f:
        assert f.readline() == content


def test_readbytes(tmp_path: PathlibPath) -> None:
    """csspin.readbytes reads from a file in which was wrote bytewise"""
    ofile = tmp_path / "test.pkl"
    content = b"Lone line"
    with open(ofile, "wb") as f:
        f.write(content)
    assert csspin.readbytes(ofile) == content


def test_writebytes(tmp_path: PathlibPath) -> None:
    """csspin.writebytes writes bytestrings to file"""
    ofile = tmp_path / "test.b"
    content = b"Lone line"
    assert csspin.writebytes(fn=ofile, data=content) == 9
    with open(ofile, "rb") as f:
        assert f.read() == content


def test_readtext(tmp_path: PathlibPath) -> None:
    """csspin.readtext reads and returns utf-8 encoded content from a file"""
    ofile = tmp_path / "test.txt"
    content = "Lone line"
    with open(ofile, "w", encoding="UTF-8") as f:
        f.write(content)
    assert csspin.readtext(ofile) == content


def test_writetext(tmp_path: PathlibPath) -> None:
    """csspin.writetext writes utf-8 stirngs to file"""
    ofile = tmp_path / "test.txt"
    content = "Lone line"
    assert csspin.writetext(fn=ofile, data=content) == 9
    with open(ofile, "r", encoding="UTF-8") as f:
        assert f.read() == content


def test_appendtext(tmp_path: PathlibPath) -> None:
    """csspin.appendtext appends utf-8 encoded strings to a file"""
    ofile = tmp_path / "test.txt"
    content = "Lone line"
    assert csspin.writetext(fn=ofile, data=content) == 9
    assert csspin.appendtext(fn=ofile, data=content) == 9
    with open(ofile, "r", encoding="UTF-8") as f:
        assert f.read() == content * 2


def test_persist(tmp_path: PathlibPath) -> None:
    """csspin.persist writes Python object(s) to file"""
    ofile = tmp_path / "test.pkl"
    to_persist = "content"
    assert csspin.persist(fn=ofile, data=to_persist) == 22
    with open(ofile, "rb") as f:
        assert pickle.loads(f.read()) == to_persist


def test_unpersist(tmp_path: PathlibPath) -> None:
    """csspin.unpersist loads Python object(s) from file"""
    ofile = tmp_path / "test.pkl"
    to_persist = "content"
    with open(ofile, "wb") as f:
        f.write(pickle.dumps(to_persist))
    assert csspin.unpersist(fn=tmp_path / "xxx") is None
    assert csspin.unpersist(fn=ofile) == to_persist


def test_memoizer(tmp_path: PathlibPath) -> None:
    """csspin.Memoizer can be instantiated and its methods perform as expected"""
    fn = tmp_path / "file.any"
    items = ["item1", "item2"]
    assert csspin.persist(fn, items) == 32
    mem = csspin.Memoizer(fn=fn)

    # pylint: disable=protected-access
    assert mem._fn == fn
    assert mem._items == items

    assert mem.check("item1")
    assert not mem.check("item")

    mem.save()
    assert csspin.unpersist(fn) == mem.items()

    assert mem.items() == items
    mem.add("item3")
    assert csspin.unpersist(fn) == mem.items()


def test_memoizer_context_manager(tmp_path: PathlibPath) -> None:
    """csspin.memoizer is useable as context manager"""
    fn = tmp_path / "file.any"
    with csspin.memoizer(fn) as mem:
        # pylint: disable=protected-access
        assert mem._fn == fn
        assert mem._items == []
        assert not mem.check("item1")

        mem.save()
        assert csspin.unpersist(fn) == []

        assert mem.items() == []
        mem.add("item1")
        assert csspin.unpersist(fn) == ["item1"]


def test_namespace_context_manager() -> None:
    """csspin.namespace can be used as context manager to modify
    csspin.NSSTACK temporarily, providing additional resolution
    namespaces.
    """
    assert not csspin.NSSTACK
    prod_ns = {"prod": "prod-value"}
    qa_ns = {"qa": "qa-value"}
    with csspin.namespaces(prod_ns, qa_ns):
        assert csspin.NSSTACK == [prod_ns, qa_ns]
        assert csspin.interpolate1("{prod}") == "prod-value"
        assert csspin.interpolate1("{qa}") == "qa-value"
    assert not csspin.NSSTACK


def test_setenv(cfg):
    """
    Test that ensures that csspin.setenv is able to set environment variables
    while resolving values to interpolate as well as those which should not
    interpolated.
    """
    cfg["FOO"] = "foo"

    # General case
    csspin.setenv(FOO="bar", BAR="foo")
    assert os.getenv("FOO") == "bar"
    assert os.getenv("BAR") == "foo"

    # With interpolation
    csspin.setenv(FOO="{FOO}")
    assert os.getenv("FOO") == "foo"

    # Who wins?
    csspin.setenv(FOO="foo", foo="bar")
    if sys.platform == "win32":
        assert os.getenv("FOO") == "bar"
    else:
        assert os.getenv("FOO") == "foo"
        assert os.getenv("foo") == "bar"


@pytest.mark.xfail(
    raises=click.exceptions.Abort,
    reason="Setenv's value must be an interpolatable string.",
)
def test_setenv_fails(cfg):
    csspin.setenv(FOO=r'{"header": {"language": "en", "cache": "bar"}}')


@patch.object(csspin, "EXPORTS", [])
@patch.dict(os.environ, {"LALA": "foo"}, clear=True)
def test_setenv_nested(cfg):
    csspin.setenv(BAR="bar:{LALA}")
    assert os.getenv("BAR") == "bar:foo"
    assert csspin.EXPORTS == [("BAR", "bar:{LALA}")]


@patch.dict(os.environ, {"FOO": "foo"})
def test_interpolate1(cfg):
    """
    csspin.interpolate1 is able to resolve variables from different sources while
    respecting the escaping syntax.
    """
    # interpolation against the environment
    assert csspin.interpolate1("'{FOO}'") == f"'{os.environ['FOO']}'"
    assert csspin.interpolate1("'{FOO}'", interpolate_environ=False) == "'{FOO}'"

    # ... one step recursion
    cfg.bad = "{bad}"
    assert csspin.interpolate1("{bad}") == "{bad}"

    # ... two step recursion
    cfg.foo = "{bar}"
    cfg.bar = "final"
    assert csspin.interpolate1("{foo}") == "final"

    # ... using a Path against the configuration tree
    cfg["BAR"] = "bar"
    result = csspin.interpolate1(Path("{BAR}"))
    assert isinstance(result, Path)
    assert result == Path("bar")

    # ... while escaping curly braces
    assert csspin.interpolate1("{{foo}}") == "{foo}"

    # ... while escaping curly braces and resolving from the ConfigTree
    assert (
        csspin.interpolate1('{{"header": {{"language": "en", "cache": "{BAR}"}}}}')
        == '{"header": {"language": "en", "cache": "bar"}}'
    )
    # ... while ensuring to escape closing curly braces right to the left
    assert csspin.interpolate1("{{{{{foo}}}}}") == "{{final}}"

    # ... triggering the RecursionError
    cfg.bad = csspin.config()
    cfg.bad.a = "{bad.b}"
    cfg.bad.b = "{bad.a}"
    with pytest.raises(
        click.Abort, match="Could not interpolate '{bad.a}' due to RecursionError."
    ):
        csspin.interpolate1("{bad.a}")

    # ... allowing to pass not path and not string
    assert csspin.interpolate1(1234) == "1234"
    assert csspin.interpolate1(str) == "<class 'str'>"


def test_interpolate_n() -> None:
    """csspin.interpolate is interpolating items of various iterables correctly"""
    assert csspin.interpolate(("a", "b", "c", None)) == ["a", "b", "c"]
    assert csspin.interpolate((1, None, 2, 3)) == ["1", "2", "3"]
    assert csspin.interpolate(((1,), None, 2, 3)) == ["(1,)", "2", "3"]


def test_config() -> None:
    """csspin.config returns csspin.ConfigTree with expected attributes"""
    assert csspin.config() == ConfigTree()
    assert csspin.config(foo="bar") == ConfigTree(foo="bar")


def test_read_yaml() -> None:
    """csspin.readyaml reads a yaml file to build the expected csspin.ConfigTree"""
    result = csspin.readyaml(
        os.path.join(os.path.dirname(__file__), "yamls", "sample.yaml")
    )
    assert result == csspin.config(foo="bar")


def test_download(cfg: ConfigTree, tmp_path: PathlibPath) -> None:
    """csspin.download is downloading the expected content to file"""
    url = "https://contact-software.com"
    location = tmp_path / "index.html"
    csspin.download(url=url, location=location)
    assert location.is_file()


def test_get_tree(cfg: ConfigTree) -> None:
    """csspin.get_tree returns the current instance of csspin.ConfigTree"""
    assert csspin.get_tree() == cfg


def test_set_tree(cfg: ConfigTree, minimum_yaml_path: str) -> None:
    """csspin.set_tree overwrites the current instance of csspin.ConfigTree"""
    assert csspin.get_tree() == cfg

    csspin.cli.load_minimal_tree(minimum_yaml_path, cwd=os.getcwd())
    new_tree = csspin.get_tree()
    assert new_tree != cfg

    from csspin import set_tree

    set_tree(cfg)
    assert csspin.get_tree() == cfg


def test_getmtime(mocker: MockerFixture, tmp_path: PathlibPath) -> None:
    """
    csspin.getmtime is returning the correct mtime for paths to be
    interpolated
    """
    mocker.patch.dict(os.environ, {"TEST_CUSTOM_FILE": "text.txt"})
    path = tmp_path / "{TEST_CUSTOM_FILE}"
    csspin.writelines(path, lines="some content")
    assert csspin.getmtime(path) == os.path.getmtime(tmp_path / "text.txt")


def test_is_up_to_date(tmp_path: PathlibPath, mocker: MockerFixture) -> None:
    """csspin.is_up_to_date compares mtimes of files correctly"""
    mocker.patch.dict(os.environ, {"TEST_CUSTOM_FILE": "text.txt"})
    path1 = tmp_path / "{TEST_CUSTOM_FILE}"
    path2 = tmp_path / "foo"
    path3 = tmp_path / "baz"

    assert not csspin.is_up_to_date(path1, 1)

    csspin.writelines(path1, lines="some content")
    with pytest.raises(click.Abort, match=r".* since 'sources' is not iterable.*"):
        csspin.is_up_to_date(path1, 1)

    from time import sleep

    sleep(0.1)
    csspin.writelines(path2, lines="some content")
    sleep(0.1)
    csspin.writelines(path3, lines="some content")

    assert csspin.is_up_to_date(path3, [path2, path1])
    assert not csspin.is_up_to_date(path1, [path2, path3])
    assert not csspin.is_up_to_date(path2, [path1, path3])


def test_run_script(mocker: MockerFixture) -> None:
    """csspin.run_script calls csspin.sh using the expected arguments"""
    mocker.patch("csspin.sh")
    csspin.run_script(script=["ls", "spin --help"], env={"foo": "bar"})
    assert (
        repr(csspin.sh.call_args_list[0])
        == "call('ls', shell=True, env={'foo': 'bar'})"
    )
    assert (
        repr(csspin.sh.call_args_list[1])
        == "call('spin --help', shell=True, env={'foo': 'bar'})"
    )
    csspin.run_script(script="ls", env={})
    assert repr(csspin.sh.call_args_list[2]) == "call('ls', shell=True, env={})"


def test_run_spin() -> None:
    """
    csspin.run_spin is calling csspin.cli.commands using the expected arguments
    """
    with pytest.raises(SystemExit):
        csspin.run_spin(script=["python", "-c", "'raise SystemExit()'"])

    with mock.patch("csspin.cli.commands"):
        csspin.run_spin(script=["ls", "spin --help"])
        assert repr(csspin.cli.commands.call_args_list[0]) == "call(['ls'])"
        assert repr(csspin.cli.commands.call_args_list[1]) == "call(['spin', '--help'])"

    with mock.patch("csspin.cli.commands"):
        csspin.run_spin(script="ls")
        assert repr(csspin.cli.commands.call_args_list[0]) == "call(['ls'])"

    with mock.patch("csspin.cli.commands"):
        csspin.run_spin(script=1)
        assert repr(csspin.cli.commands.call_args_list[0]) == "call(['1'])"


def test_get_sources(cfg: ConfigTree) -> None:
    """
    csspin.sources retrieves either the tree's 'sources' attribute values as
    list or and an empty list
    """
    assert csspin.get_sources(cfg) == []

    cfg["sources"] = "foo"
    assert csspin.get_sources(cfg) == ["foo"]

    cfg["sources"] = ["foo", "bar"]
    assert csspin.get_sources(cfg) == ["foo", "bar"]


def test_build_target(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """
    csspin.build_target extends the ConfigTree and is called using the expected
    arguments
    """
    cfg["build_rules"] = csspin.config(
        phony=csspin.config(sources="notphony"),
        notphony=csspin.config(script=["1", "2"]),
    )
    # According to the rule above, building "phony" would require
    # "notphony" to exist, which would be produced by calling 1 and 2.
    mocker.patch(
        "subprocess.run",
        side_effect=lambda *args, **kwargs: subprocess.CompletedProcess(args, 0),
    )
    csspin.build_target(cfg, "phony", True)
    assert [c.args[0][0] for c in subprocess.run.call_args_list] == ["1", "2"]  # type: ignore[attr-defined]


def test_build_target_no_target(cfg: ConfigTree) -> None:
    """csspin.build_target fails if 'target' is not found"""
    with pytest.raises(
        click.Abort, match=".*Sorry, I don't know.* 'NOT_EXISTING_THING'.*"
    ):
        csspin.build_target(cfg, target="NOT_EXISTING_THING")


def test_build_target_no_target_but_exists(
    cfg: ConfigTree, tmp_path: PathlibPath
) -> None:
    """
    csspin.build_target will not fail but do nothing if the target not in the
    tree's build rules, but still exist
    """
    cfg["TMPDIR"] = tmp_path
    csspin.build_target(cfg, target="{TMPDIR}")


def test_build_target_up_to_date(
    cfg: ConfigTree,
    mocker: MockerFixture,
    tmp_path: PathlibPath,
) -> None:
    """csspin.build_target will not build anything if the target is up-to-date"""
    mocker.patch("csspin.info")
    cfg["TMPDIR"] = tmp_path
    cfg["build_rules"] = csspin.config()
    cfg["build_rules"]["{TMPDIR}"] = csspin.config(script=["mkdir", "{TMPDIR}"])
    csspin.build_target(cfg, "{TMPDIR}", False)
    assert "{TMPDIR} is up to date" in str(csspin.info.call_args_list[1])


def test_ensure(mocker: MockerFixture) -> None:
    """csspin.ensure is calling csspin.build_target using the expected arguments"""

    @csspin.task()
    def command() -> None:
        """Just a command"""

    mocker.patch("csspin.build_target")
    csspin.ensure(command)
    assert csspin.build_target.call_args_list[0][0][-1] == "task command"
    assert str(csspin.build_target.call_args_list[0][1]) == "{'phony': True}"


def test_argument() -> None:
    """
    csspin.argument is returning a wrapper function which can be used to modify
    commands
    """
    argument = csspin.argument()
    assert isinstance(argument, Callable)
    assert isinstance(argument("name"), Callable)

    argument = csspin.argument(type=str, required=True)
    task = csspin.task("test")

    def test_command() -> None:
        pass

    decorated_command = argument("param")(task(test_command))
    assert decorated_command.params[0].name == "param"
    assert isinstance(decorated_command.params[0].type, click.types.StringParamType)
    assert decorated_command.params[0].required

    with pytest.raises(TypeError, match=".* got an unexpected keyword argument 'help'"):
        argument = csspin.argument(help="Arguments must not implement 'help'")
        argument("param")(task(test_command))


def test_option() -> None:
    """
    csspin.option is returning a wrapper function which can be used to modify
    commands
    """
    task = csspin.task("test")
    option = csspin.option("-p", "--param", type=str, required=True, help="Help me!")(
        "param"
    )
    assert isinstance(option, Callable)

    def test_command() -> None:
        pass

    decorated_command = option(task(test_command))
    assert decorated_command.params[0].name == "param"
    assert isinstance(decorated_command.params[0].type, click.types.StringParamType)
    assert decorated_command.params[0].required
    assert decorated_command.params[0].help == "Help me!"


def test_task_regular() -> None:
    """
    csspin.task is returning a wrapper function which will build and return a task
    object with regular_callback #1
    """
    wrapper = csspin.task()
    assert isinstance(wrapper, Callable)

    def test_command_regular(args: Any) -> Any:
        """Function used for applying csspin.task"""
        return args

    task = wrapper(test_command_regular)
    assert isinstance(task, Callable)
    assert task.name == "test-command-regular"
    assert task.context_settings["ignore_unknown_options"]
    assert task.context_settings["allow_extra_args"]
    assert "regular_callback" in str(task.callback)
    assert task.__doc__ == "Function used for applying csspin.task"
    assert task.callback("bar") == "bar"


def test_task_ctx() -> None:
    """
    csspin.task is returning a wrapper function which will build and return a task
    object with regular_callback #2
    """
    wrapper = csspin.task()

    def test_command_ctx(ctx: click.Context, args: Any) -> dict:
        return ctx.obj

    task = wrapper(test_command_ctx)
    assert task.name == "test-command-ctx"
    assert "regular_callback" in str(task.callback)
    with click.Context(click.Command(""), obj={"foo": "bar"}) as ctx:
        assert task.callback(ctx) == {"foo": "bar"}


def test_task_cfg(cfg: ConfigTree) -> None:
    """
    csspin.task is returning a wrapper function which will build and return a task
    object with alternate_callback
    """
    from csspin import cli

    wrapper = csspin.task(noenv=True, when="dummy-hook")

    def test_command_cfg(cfg: ConfigTree, args: Any) -> str:
        return "foo"

    task = wrapper(test_command_cfg)

    assert task.name == "test-command-cfg"
    assert isinstance(task.context_settings, ConfigTree)
    assert "alternate_callback" in str(task.callback)
    assert task.callback(cfg) == "foo"
    assert "test-command-cfg" in cli.NOENV_COMMANDS
    assert "dummy-hook" in cfg.spin.hooks


def test_group(cfg: ConfigTree) -> None:
    """csspin.group can be used to define command groups with subcommands"""
    from csspin import cli

    @csspin.group("foo", noenv=True)
    def foo(ctx: click.Context) -> None:  # pylint: disable=disallowed-name
        """Subcommands used for testing"""

    assert isinstance(foo, csspin.cli.GroupWithAliases)
    assert "foo" in cli.NOENV_COMMANDS
    assert foo.__doc__ == "Subcommands used for testing"

    @foo.task("bar")
    def bar() -> str:  # pylint: disable=disallowed-name
        return "foo"

    assert "bar" in foo.commands
    assert foo.commands["bar"] is bar  # pylint: disable=comparison-with-callable
    assert foo.commands["bar"].callback() == bar.callback() == "foo"

    @foo.task("buz")
    def buz(cfg: ConfigTree) -> ConfigTree:
        return cfg

    assert list(foo.commands.keys()) == ["bar", "buz"]


def test_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """csspin.invoke is able to invoke tasks marked to run 'when="lint"'"""
    calls = []

    def mock_print(*args: Any) -> None:
        calls.append(args)

    monkeypatch.setattr("builtins.print", mock_print)

    @csspin.task(when="lint")
    def pylint() -> None:
        """Should be invoked by 'lint'"""
        print("pylint")

    @csspin.task(when="lint")
    def flake8() -> None:
        """Should be invoked by 'lint'"""
        print("flake8")

    @csspin.task()
    def parse() -> None:  # pylint: disable=unused-variable
        """Should not be invoked by 'lint'"""
        print("parse")

    with click.Context(click.Command("")):
        csspin.invoke("lint")
    assert calls == [("pylint",), ("flake8",)]


def test_parse_version() -> None:
    """
    csspin.parse_version is parsing version strings correctly into
    packaging.version.Version instances
    """
    from packaging.version import InvalidVersion, Version

    version_str = "1.2.3"
    parsed_version = csspin.parse_version(version_str)

    assert isinstance(parsed_version, Version)
    assert str(parsed_version) == version_str

    with pytest.raises(InvalidVersion):
        csspin.parse_version("invalid_version")


def test_get_requires(cfg: ConfigTree) -> None:
    """
    csspin.requires is returning the expected 'requires' values for a +subtree
    """
    assert csspin.get_requires(cfg, "build") == []
    foo_requires = csspin.config(build="foo")
    cfg["requires"] = csspin.config(foo=foo_requires)
    assert csspin.get_requires(cfg, "foo") is foo_requires


def test_toporun(
    cfg: ConfigTree,
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """csspin.toporun executes a specific function of a loaded plugin"""
    # TODO: Load another plugin that implements `configure` (or another function
    #       which is implemented in csspin.builtin) and test the reversed
    #       execution.
    mocker.patch("csspin.builtin.configure", return_value=None)
    cfg.verbosity = Verbosity.DEBUG

    csspin.toporun(cfg, "configure")

    captured = capsys.readouterr()
    assert "toporun: configure" in captured.out
