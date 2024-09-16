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

import logging
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

import spin
from spin.tree import ConfigTree

if TYPE_CHECKING:

    from typing import Any

    from pytest import LogCaptureFixture
    from pytest_mock.plugin import MockerFixture


def test_echo(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """spin.echo is echo'ing when CONFIG.quiet is False"""
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    spin.echo(marker)
    for call in click.echo.call_args_list:  # type: ignore[attr-defined]
        assert any(
            expected in call.args[0] for expected in ("spin: ", marker)
        ), f"None of the expected values found in {call.args[0]=}"


def test_echo_quiet(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """spin.echo is not echo'ing if CONFIG.quiet is True"""
    mocker.patch("click.echo")
    cfg.quiet = True

    spin.echo("Should not be shown")
    assert not click.echo.called  # type: ignore[attr-defined]


def test_info(mocker: MockerFixture) -> None:
    """spin.info is info'ing if CONFIG.verbose is False"""
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    spin.info(marker)
    assert not click.echo.called  # type: ignore[attr-defined]


def test_info_verbose(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """spin.info is info'ing if CONFIG.verbose is True"""
    mocker.patch("click.echo")
    marker = "ZIOhddu"
    cfg.verbose = True
    spin.info(marker)
    for call in click.echo.call_args_list:  # type: ignore[attr-defined]
        assert any(
            expected in call.args[0] for expected in ("spin: ", marker)
        ), f"None of the expected values found in {call.args[0]=}"


@pytest.mark.parametrize(
    "function,message",
    ((spin.warn, "warning"), (spin.error, "error")),
)
def test_echo_extended(function: Callable, message: str, mocker: MockerFixture) -> None:
    f"""spin.{message} gets called using the expected arguments."""  # pylint: disable=pointless-statement
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
    """spin.DirectoryChanger is able to change directories accordingly"""
    cfg.quiet = False
    cwd = os.getcwd()
    mocker.patch("click.echo")

    with spin.DirectoryChanger(path=tmp_path):
        assert os.getcwd() == str(tmp_path)
        assert str(tmp_path) in repr(click.echo.call_args_list).replace("\\\\", "\\")  # type: ignore[attr-defined] # noqa: E501
    assert os.getcwd() == cwd

    # if nothing to do, directory changer does nothing and echoes nothing
    with spin.DirectoryChanger(path=cwd):
        assert os.getcwd() == cwd
        assert cwd not in repr(click.echo.call_args_list).replace("\\\\", "\\")  # type: ignore[attr-defined]


def test_cd(tmp_path: PathlibPath) -> None:
    """spin.cd is changing the current directory as expected"""
    cwd = os.getcwd()
    with spin.cd(tmp_path):
        assert os.getcwd() == str(tmp_path)
    assert cwd == os.getcwd()


def test_exists(cfg: ConfigTree, tmp_path: PathlibPath) -> None:
    """spin.exists is able to validate the existence of directories"""
    cfg["TMPDIR"] = tmp_path
    assert os.path.isdir(tmp_path)
    assert spin.exists("{TMPDIR}")
    assert spin.exists(tmp_path)
    assert not spin.exists(r"\foo/bar\baz/biz\buz")


def test_normpath(cfg: ConfigTree) -> None:
    """
    spin.normpath is resolving environment variables to return the normalized
    path
    """
    cfg["FOO"] = "foo"
    assert spin.normpath("{FOO}") == os.path.normpath("foo")


def test_abspath(cfg: ConfigTree) -> None:
    """
    spin.abspath is resolving environment variables to return the absolute path
    """
    cfg["FOO"] = "foo"
    assert spin.abspath("{FOO}") == os.path.abspath("foo")


def test_mkdir(tmp_path: PathlibPath) -> None:
    """
    spin.mkdir is able to create directories and will not fail if the directory
    already exists
    """
    spin.mkdir(tmp_path)
    path = tmp_path / "foo"
    spin.mkdir(path)
    assert os.path.isdir(path)


def test_mkdir_rmdir(tmp_path: PathlibPath) -> None:
    """spin.rmdir is able to delete directories"""
    xxx = tmp_path / "xxx"
    assert not spin.exists(xxx)
    spin.mkdir(xxx)
    assert spin.exists(xxx)
    spin.rmtree(xxx)
    assert not spin.exists(xxx)


def test_mv(tmp_path: PathlibPath) -> None:
    """spin.mv is able to move and rename files and directories"""
    from tempfile import mktemp

    with pytest.raises(click.Abort, match=".* does not exist!"):
        spin.mv(mktemp(), tmp_path)

    subdir_a = tmp_path / "sub_a"
    subdir_b = tmp_path / "sub_b"
    subdir_a.mkdir()
    subdir_b.mkdir()
    file_ = subdir_a / "file.txt"
    file_.write_text("")

    # move file
    spin.mv(file_, subdir_b)
    assert (subdir_b / "file.txt").is_file()
    assert not file_.is_file()

    # move directory
    spin.mv(subdir_b, subdir_a)
    assert ((file_path := subdir_a / "sub_b" / "file.txt")).is_file()
    assert not subdir_b.is_dir()

    # rename file
    spin.mv(file_path, (new_file_path := subdir_a / "sub_b" / "file2.txt"))
    assert not file_path.is_file()
    assert new_file_path.is_file()


def test_copy(tmp_path: PathlibPath) -> None:
    """spin.copy is able to copy files and directories to the desired
    locations
    """
    source_dir = tmp_path / "directory"
    source_dir.mkdir()
    file_ = source_dir / "file.txt"
    file_.write_text("foo")
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # copy file
    spin.copy(file_, target_dir)
    assert file_.is_file()
    assert (target_dir / "file.txt").is_file()

    # copy directory
    spin.copy(source_dir, target_dir)
    assert (target_dir / "directory" / "file.txt").is_file()


def test_die() -> None:
    """spin.die will raise click.Abort"""
    with pytest.raises(click.Abort, match="You shall not pass!"):
        spin.die("You shall not pass!")


def test_command() -> None:
    """
    spin.command will instantiate the spin.Command class which is able to call
    its basic functions
    """
    # pylint: disable=protected-access
    cmd = spin.Command("pip", "list")
    assert cmd._cmd == ["pip", "list"]

    cmd.append("--help")
    assert cmd._cmd == ["pip", "list", "--help"]


def test_sh(mocker: MockerFixture) -> None:
    """
    spin.sh will raise the expected errors on faulty input as well as execute
    valid commands by calling subprocess.run with the correct arguments
    """
    with pytest.raises(
        click.Abort,
        match=(
            ".*WinError 2.*"
            if sys.platform == "win32"
            else ".*No such file or directory.*FileNotFoundTrigger.*"
        ),
    ):
        spin.sh("FileNotFoundTrigger", shell=False)

    with mock.patch("spin.warn") as spin_warn:
        spin.sh("FileNotFoundTrigger", shell=False, may_fail=True)
        warning = (
            "WinError 2"
            if sys.platform == "win32"
            else "[Errno 2] No such file or directory: 'FileNotFoundTrigger'"
        )
        assert any(warning in arg for arg in spin_warn.call_args.args)

    with pytest.raises(
        click.Abort,
        match=".*Command.*'CalledProcessErrorTrigger'.*failed with return code.*",
    ):
        spin.sh("CalledProcessErrorTrigger")

    with mock.patch("spin.warn") as spin_warn:
        spin.sh("CalledProcessErrorTrigger", may_fail=True)
        assert any(
            "Command 'CalledProcessErrorTrigger' failed with return code" in arg
            for arg in spin_warn.call_args.args
        )

    spin.sh("FileNotFoundTrigger", shell=False, may_fail=True)

    mocker.patch("subprocess.run")
    spin.sh("abc", "123 4")
    assert subprocess.run.call_args.args[0] == ["abc", "123 4"]  # type: ignore[attr-defined]

    if sys.platform == "win32":
        spin.sh("abc 123")
        assert subprocess.run.call_args.args[0] == ["abc", "123"]

    env = {"_OJDS": "x"}
    spin.sh("abc", "123", env=env)
    assert "env" in subprocess.run.call_args.kwargs  # type: ignore[attr-defined]
    assert "_OJDS" in subprocess.run.call_args.kwargs["env"]  # type: ignore[attr-defined]


def test_backtick(mocker: MockerFixture) -> None:
    """
    spin.backtick is calling spin.sh using the correct arguments and returning
    the expected value
    """
    from socket import gethostname

    assert spin.backtick("hostname") == f"{gethostname()}{os.linesep}"

    mocker.patch("spin.sh")
    spin.backtick("hostname")
    spin.sh.assert_called_with("hostname", stdout=-1)


def test__read_file(minimum_yaml_path: str) -> None:
    """spin._read_file reads from file and returns the content"""
    # pylint: disable=protected-access
    expected = "foo: bar\n"
    assert spin._read_file(fn=minimum_yaml_path, mode="r") == expected

    with mock.patch.dict(os.environ, {"TEST_MINIMUM_YAML_PATH": minimum_yaml_path}):
        assert spin._read_file(fn="{TEST_MINIMUM_YAML_PATH}", mode="r") == expected


def test__read_lines(minimum_yaml_path: str) -> None:
    """spin._read_lines is able to read and return multiple lines from a file"""
    # pylint: disable=protected-access
    expected = ["foo: bar\n"]
    assert spin.readlines(fn=minimum_yaml_path) == expected
    with mock.patch.dict(os.environ, {"TEST_MINIMUM_YAML_PATH": minimum_yaml_path}):
        assert spin.readlines(fn="{TEST_MINIMUM_YAML_PATH}") == expected


def test_writelines(tmp_path: PathlibPath) -> None:
    """spin.writelines writes multiple lines into a file"""
    content = "foo:\n  - bar\n  - baz"
    expected = ["foo:\n", "  - bar\n", "  - baz"]
    assert spin.writelines(fn=tmp_path / "test.txt", lines=content) is None
    with open(tmp_path / "test.txt", "r", encoding="utf-8") as f:
        assert f.readlines() == expected


def test_write_file(tmp_path: PathlibPath) -> None:
    """spin.write_file writes a string to file"""
    # pylint: disable=protected-access
    ofile = tmp_path / "test.txt"
    content = "Lone line"
    spin._write_file(ofile, mode="w", data=content)
    assert os.path.isfile(ofile)
    with open(ofile, "r", encoding="UTF-8") as f:
        assert f.readline() == content


def test_readbytes(tmp_path: PathlibPath) -> None:
    """spin.readbytes reads from a file in which was wrote bytewise"""
    ofile = tmp_path / "test.pkl"
    content = b"Lone line"
    with open(ofile, "wb") as f:
        f.write(content)
    assert spin.readbytes(ofile) == content


def test_writebytes(tmp_path: PathlibPath) -> None:
    """spin.writebytes writes bytestrings to file"""
    ofile = tmp_path / "test.b"
    content = b"Lone line"
    assert spin.writebytes(fn=ofile, data=content) == 9
    with open(ofile, "rb") as f:
        assert f.read() == content


def test_readtext(tmp_path: PathlibPath) -> None:
    """spin.readtext reads and returns utf-8 encoded content from a file"""
    ofile = tmp_path / "test.txt"
    content = "Lone line"
    with open(ofile, "w", encoding="UTF-8") as f:
        f.write(content)
    assert spin.readtext(ofile) == content


def test_writetext(tmp_path: PathlibPath) -> None:
    """spin.writetext writes utf-8 stirngs to file"""
    ofile = tmp_path / "test.txt"
    content = "Lone line"
    assert spin.writetext(fn=ofile, data=content) == 9
    with open(ofile, "r", encoding="UTF-8") as f:
        assert f.read() == content


def test_appendtext(tmp_path: PathlibPath) -> None:
    """spin.appendtext appends utf-8 encoded strings to a file"""
    ofile = tmp_path / "test.txt"
    content = "Lone line"
    assert spin.writetext(fn=ofile, data=content) == 9
    assert spin.appendtext(fn=ofile, data=content) == 9
    with open(ofile, "r", encoding="UTF-8") as f:
        assert f.read() == content * 2


def test_persist(tmp_path: PathlibPath) -> None:
    """spin.persist writes Python object(s) to file"""
    ofile = tmp_path / "test.pkl"
    to_persist = "content"
    assert spin.persist(fn=ofile, data=to_persist) == 22
    with open(ofile, "rb") as f:
        assert pickle.loads(f.read()) == to_persist


def test_unpersist(tmp_path: PathlibPath) -> None:
    """spin.unpersist loads Python object(s) from file"""
    ofile = tmp_path / "test.pkl"
    to_persist = "content"
    with open(ofile, "wb") as f:
        f.write(pickle.dumps(to_persist))
    assert spin.unpersist(fn=tmp_path / "xxx") is None
    assert spin.unpersist(fn=ofile) == to_persist


def test_memoizer(tmp_path: PathlibPath) -> None:
    """spin.Memoizer can be instantiated and its methods perform as expected"""
    fn = tmp_path / "file.any"
    items = ["item1", "item2"]
    assert spin.persist(fn, items) == 32
    mem = spin.Memoizer(fn=fn)

    # pylint: disable=protected-access
    assert mem._fn == fn
    assert mem._items == items

    assert mem.check("item1")
    assert not mem.check("item")

    mem.save()
    assert spin.unpersist(fn) == mem.items()

    assert mem.items() == items
    mem.add("item3")
    assert spin.unpersist(fn) == mem.items()


def test_memoizer_context_manager(tmp_path: PathlibPath) -> None:
    """spin.memoizer is useable as context manager"""
    fn = tmp_path / "file.any"
    with spin.memoizer(fn) as mem:
        # pylint: disable=protected-access
        assert mem._fn == fn
        assert mem._items == []
        assert not mem.check("item1")

        mem.save()
        assert spin.unpersist(fn) == []

        assert mem.items() == []
        mem.add("item1")
        assert spin.unpersist(fn) == ["item1"]


def test_namespace_context_manager() -> None:
    """
    spin.namespace can be used as context manager to modify spin.NSSTACK
    temporary
    """
    assert not spin.NSSTACK
    with spin.namespaces("prod", "qa"):
        assert spin.NSSTACK == ["prod", "qa"]
    assert not spin.NSSTACK


def test_setenv(cfg):
    """
    Test that ensures that spin.setenv is able to set environment variables
    while resolving values to interpolate as well as those which should not
    interpolated.
    """
    cfg["FOO"] = "foo"

    spin.setenv(FOO="bar", BAR="foo")
    assert os.getenv("FOO") == "bar"
    assert os.getenv("BAR") == "foo"
    spin.setenv(FOO="{FOO}")
    assert os.getenv("FOO") == "foo"


@patch.dict(os.environ, {"FOO": "foo"})
def test_interpolate1(cfg):
    """
    spin.interpolate1 is able to resolve variables from different sources while
    respecting the escaping syntax.
    """
    # interpolation against the environment
    assert spin.interpolate1("'{FOO}'") == f"'{os.environ['FOO']}'"

    # ... one step recursion
    cfg.bad = "{bad}"
    assert spin.interpolate1("{bad}") == "{bad}"

    # ... two step recursion
    cfg.foo = "{bar}"
    cfg.bar = "final"
    assert spin.interpolate1("{foo}") == "final"

    # ... using a Path against the configuration tree
    cfg["BAR"] = "bar"
    result = spin.interpolate1(Path("{BAR}"))
    assert isinstance(result, Path)
    assert result == Path("bar")

    # ... while escaping curly braces
    assert spin.interpolate1("{{foo}}") == "{foo}"

    # ... while escaping curly braces and resolving from the ConfigTree
    assert (
        spin.interpolate1('{{"header": {{"language": "en", "cache": "{BAR}"}}}}')
        == '{"header": {"language": "en", "cache": "bar"}}'
    )
    # ... while ensuring to escape closing curly braces right to the left
    assert spin.interpolate1("{{{{{foo}}}}}") == "{{final}}"

    # ... triggering the RecursionError
    cfg.bad = spin.config()
    cfg.bad.a = "{bad.b}"
    cfg.bad.b = "{bad.a}"
    with pytest.raises(
        click.Abort, match="Could not interpolate '{bad.a}' due to RecursionError."
    ):
        spin.interpolate1("{bad.a}")

    # ... allowing to pass not path and not string
    assert spin.interpolate1(1234) == "1234"
    assert spin.interpolate1(str) == "<class 'str'>"


def test_interpolate_n() -> None:
    """spin.interpolate is interpolating items of various iterables correctly"""
    assert spin.interpolate(("a", "b", "c", None)) == ["a", "b", "c"]
    assert spin.interpolate((1, None, 2, 3)) == ["1", "2", "3"]
    assert spin.interpolate(((1,), None, 2, 3)) == ["(1,)", "2", "3"]


def test_config() -> None:
    """spin.config returns spin.ConfigTree with expected attributes"""
    assert spin.config() == ConfigTree()
    assert spin.config(foo="bar") == ConfigTree(foo="bar")


def test_read_yaml() -> None:
    """spin.readyaml reads a yaml file to build the expected spin.ConfigTree"""
    result = spin.readyaml(
        os.path.join(os.path.dirname(__file__), "yamls", "sample.yaml")
    )
    assert result == spin.config(foo="bar")


def test_download(cfg: ConfigTree, tmp_path: PathlibPath) -> None:
    """spin.download is downloading the expected content to file"""
    cfg.quiet = True
    url = "https://contact-software.com"
    location = tmp_path / "index.html"
    spin.download(url=url, location=location)
    assert location.is_file()


def test_get_tree(cfg: ConfigTree) -> None:
    """spin.get_tree returns the current instance of spin.ConfigTree"""
    assert spin.get_tree() == cfg


def test_set_tree(cfg: ConfigTree, minimum_yaml_path: str) -> None:
    """spin.set_tree overwrites the current instance of spin.ConfigTree"""
    assert spin.get_tree() == cfg

    spin.cli.load_config_tree(minimum_yaml_path, cwd=os.getcwd())
    new_tree = spin.get_tree()
    assert new_tree != cfg

    from spin import set_tree

    set_tree(cfg)
    assert spin.get_tree() == cfg


def test_getmtime(mocker: MockerFixture, tmp_path: PathlibPath) -> None:
    """
    spin.getmtime is returning the correct mtime for paths to be
    interpolated
    """
    mocker.patch.dict(os.environ, {"TEST_CUSTOM_FILE": "text.txt"})
    path = tmp_path / "{TEST_CUSTOM_FILE}"
    spin.writelines(path, lines="some content")
    assert spin.getmtime(path) == os.path.getmtime(tmp_path / "text.txt")


def test_is_up_to_date(tmp_path: PathlibPath, mocker: MockerFixture) -> None:
    """spin.is_up_to_date compares mtimes of files correctly"""
    mocker.patch.dict(os.environ, {"TEST_CUSTOM_FILE": "text.txt"})
    path1 = tmp_path / "{TEST_CUSTOM_FILE}"
    path2 = tmp_path / "foo"
    path3 = tmp_path / "baz"

    assert not spin.is_up_to_date(path1, 1)

    spin.writelines(path1, lines="some content")
    with pytest.raises(click.Abort, match=r".* since 'sources' is not iterable.*"):
        spin.is_up_to_date(path1, 1)

    from time import sleep

    sleep(0.1)
    spin.writelines(path2, lines="some content")
    sleep(0.1)
    spin.writelines(path3, lines="some content")

    assert spin.is_up_to_date(path3, [path2, path1])
    assert not spin.is_up_to_date(path1, [path2, path3])
    assert not spin.is_up_to_date(path2, [path1, path3])


def test_run_script(mocker: MockerFixture) -> None:
    """spin.run_script calls spin.sh using the expected arguments"""
    mocker.patch("spin.sh")
    spin.run_script(script=["ls", "spin --help"], env={"foo": "bar"})
    assert (
        repr(spin.sh.call_args_list[0]) == "call('ls', shell=True, env={'foo': 'bar'})"
    )
    assert (
        repr(spin.sh.call_args_list[1])
        == "call('spin --help', shell=True, env={'foo': 'bar'})"
    )
    spin.run_script(script="ls", env={})
    assert repr(spin.sh.call_args_list[2]) == "call('ls', shell=True, env={})"


def test_run_spin() -> None:
    """
    spin.run_spin is calling spin.cli.commands using the expected arguments
    """
    with pytest.raises(SystemExit):
        spin.run_spin(script=["python", "-c", "'raise SystemExit()'"])

    with mock.patch("spin.cli.commands"):
        spin.run_spin(script=["ls", "spin --help"])
        assert repr(spin.cli.commands.call_args_list[0]) == "call(['ls'])"
        assert repr(spin.cli.commands.call_args_list[1]) == "call(['spin', '--help'])"

    with mock.patch("spin.cli.commands"):
        spin.run_spin(script="ls")
        assert repr(spin.cli.commands.call_args_list[0]) == "call(['ls'])"

    with mock.patch("spin.cli.commands"):
        spin.run_spin(script=1)
        assert repr(spin.cli.commands.call_args_list[0]) == "call(['1'])"


def test_get_sources(cfg: ConfigTree) -> None:
    """
    spin.sources retrieves either the tree's 'sources' attribute values as
    list or and an empty list
    """
    assert spin.get_sources(cfg) == []

    cfg["sources"] = "foo"
    assert spin.get_sources(cfg) == ["foo"]

    cfg["sources"] = ["foo", "bar"]
    assert spin.get_sources(cfg) == ["foo", "bar"]


def test_build_target(cfg: ConfigTree, mocker: MockerFixture) -> None:
    """
    spin.build_target extends the ConfigTree and is called using the expected
    arguments
    """
    mocker.patch("subprocess.run")
    cfg["build-rules"] = spin.config(
        phony=spin.config(sources="notphony"),
        notphony=spin.config(script=["1", "2"]),
    )
    # According to the rule above, building "phony" would require
    # "notphony" to exist, which would be produced by calling 1 and 2.
    spin.build_target(cfg, "phony", True)
    assert [c.args[0][0] for c in subprocess.run.call_args_list] == ["1", "2"]  # type: ignore[attr-defined]


def test_build_target_no_target(cfg: ConfigTree) -> None:
    """spin.build_target fails if 'target' is not found"""
    with pytest.raises(
        click.Abort, match=".*Sorry, I don't know.* 'NOT_EXISTING_THING'.*"
    ):
        spin.build_target(spin.config(), target="NOT_EXISTING_THING")


def test_build_target_no_target_but_exists(
    cfg: ConfigTree, tmp_path: PathlibPath
) -> None:
    """
    spin.build_target will not fail but do nothing if the target not in the
    tree's build rules, but still exist
    """
    cfg["TMPDIR"] = tmp_path
    spin.build_target(spin.config(), target="{TMPDIR}")


def test_build_target_up_to_date(
    cfg: ConfigTree,
    mocker: MockerFixture,
    tmp_path: PathlibPath,
) -> None:
    """spin.build_target will not build anything if the target is up-to-date"""
    mocker.patch("spin.info")
    cfg["TMPDIR"] = tmp_path
    cfg["build-rules"] = spin.config()
    cfg["build-rules"]["{TMPDIR}"] = spin.config(script=["mkdir", "{TMPDIR}"])
    spin.build_target(cfg, "{TMPDIR}", False)
    assert "{TMPDIR} is up to date" in str(spin.info.call_args_list[1])


def test_ensure(mocker: MockerFixture) -> None:
    """spin.ensure is calling spin.build_target using the expected arguments"""

    @spin.task()
    def command() -> None:
        """Just a command"""

    mocker.patch("spin.build_target")
    spin.ensure(command)
    assert spin.build_target.call_args_list[0][0][-1] == "task command"
    assert str(spin.build_target.call_args_list[0][1]) == "{'phony': True}"


def test_argument() -> None:
    """
    spin.argument is returning a wrapper function which can be used to modify
    commands
    """
    argument = spin.argument()
    assert isinstance(argument, Callable)
    assert isinstance(argument("name"), Callable)

    argument = spin.argument(type=str, required=True)
    task = spin.task("test")

    def test_command() -> None:
        pass

    decorated_command = argument("param")(task(test_command))
    assert decorated_command.params[0].name == "param"
    assert isinstance(decorated_command.params[0].type, click.types.StringParamType)
    assert decorated_command.params[0].required

    with pytest.raises(TypeError, match=".* got an unexpected keyword argument 'help'"):
        argument = spin.argument(help="Arguments must not implement 'help'")
        argument("param")(task(test_command))


def test_option() -> None:
    """
    spin.option is returning a wrapper function which can be used to modify
    commands
    """
    task = spin.task("test")
    option = spin.option("-p", "--param", type=str, required=True, help="Help me!")(
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
    spin.task is returning a wrapper function which will build and return a task
    object with regular_callback #1
    """
    wrapper = spin.task()
    assert isinstance(wrapper, Callable)

    def test_command_regular(args: Any) -> Any:
        """Function used for applying spin.task"""
        return args

    task = wrapper(test_command_regular)
    assert isinstance(task, Callable)
    assert task.name == "test-command-regular"
    assert task.context_settings["ignore_unknown_options"]
    assert task.context_settings["allow_extra_args"]
    assert "regular_callback" in str(task.callback)
    assert task.__doc__ == "Function used for applying spin.task"
    assert task.callback("bar") == "bar"


def test_task_ctx() -> None:
    """
    spin.task is returning a wrapper function which will build and return a task
    object with regular_callback #2
    """
    wrapper = spin.task()

    def test_command_ctx(ctx: click.Context, args: Any) -> dict:
        return ctx.obj

    task = wrapper(test_command_ctx)
    assert task.name == "test-command-ctx"
    assert "regular_callback" in str(task.callback)
    with click.Context(click.Command(""), obj={"foo": "bar"}) as ctx:
        assert task.callback(ctx) == {"foo": "bar"}


def test_task_cfg(cfg: ConfigTree) -> None:
    """
    spin.task is returning a wrapper function which will build and return a task
    object with alternate_callback
    """
    from spin import cli

    wrapper = spin.task(noenv=True, when="dummy-hook")

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
    """spin.group can be used to define command groups with subcommands"""
    from spin import cli

    @spin.group("foo", noenv=True)
    def foo(ctx: click.Context) -> None:  # pylint: disable=disallowed-name
        """Subcommands used for testing"""

    assert isinstance(foo, spin.cli.GroupWithAliases)
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
    """spin.invoke is able to invoke tasks marked to run 'when="lint"'"""
    calls = []

    def mock_print(*args: Any) -> None:
        calls.append(args)

    monkeypatch.setattr("builtins.print", mock_print)

    @spin.task(when="lint")
    def pylint() -> None:
        """Should be invoked by 'lint'"""
        print("pylint")

    @spin.task(when="lint")
    def flake8() -> None:
        """Should be invoked by 'lint'"""
        print("flake8")

    @spin.task()
    def parse() -> None:  # pylint: disable=unused-variable
        """Should not be invoked by 'lint'"""
        print("parse")

    with click.Context(click.Command("")):
        spin.invoke("lint")
    assert calls == [("pylint",), ("flake8",)]


def test_parse_version() -> None:
    """
    spin.parse_version is parsing version strings correctly into
    packaging.version.Version instances
    """
    from packaging.version import InvalidVersion, Version

    version_str = "1.2.3"
    parsed_version = spin.parse_version(version_str)

    assert isinstance(parsed_version, Version)
    assert str(parsed_version) == version_str

    with pytest.raises(InvalidVersion):
        spin.parse_version("invalid_version")


def test_get_requires(cfg: ConfigTree) -> None:
    """
    spin.requires is returning the expected 'requires' values for a +subtree
    """
    assert spin.get_requires(cfg, "build") == []
    foo_requires = spin.config(build="foo")
    cfg["requires"] = spin.config(foo=foo_requires)
    assert spin.get_requires(cfg, "foo") is foo_requires


def test_toporun(
    mocker: MockerFixture,
    cfg: ConfigTree,
    caplog: LogCaptureFixture,
) -> None:
    """spin.toporun executes a specific function of a loaded plugin"""
    # TODO: Load another plugin that implements `configure` (or another function
    #       which is implemented in spin.builtin) and test the reversed
    #       execution.
    mocker.patch("spin.builtin.configure", return_value=None)
    caplog.set_level(logging.DEBUG)
    assert spin.toporun(cfg, "configure") is None
    assert "toporun: configure" in caplog.text
    assert "spin.builtin.configure()" in caplog.text
