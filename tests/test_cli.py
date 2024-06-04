# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""Module implementing the unit tests regarding the cli.py module of cs.spin"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path as PathlibPath
from shutil import copy
from typing import TYPE_CHECKING, Callable, Generator

import click
import pytest
from conftest import chdir
from path import Path

from spin import cli
from spin.tree import ConfigTree

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest import LogCaptureFixture
    from pytest_mock.plugin import MockerFixture


def test_cli(cli_runner: CliRunner) -> None:
    """spin.cli can be invoked using click"""
    result = cli_runner.invoke(cli.cli, ["--help"])
    assert result.exit_code == 0


def test_find_spinfile(tmp_path: PathlibPath) -> None:
    """
    spin.cli.find_spinfile is able to find the passed spinfile and returning
    None if not and the default location if None was passed
    """
    spinfile = os.path.normpath(f"{tmp_path}/spinfile.yaml")
    with open(spinfile, "w", encoding="utf-8") as f:
        f.write("")

    insidetree = f"{tmp_path}/a/b/c"
    os.makedirs(insidetree)
    with chdir(insidetree):
        assert cli.find_spinfile("spinfile.yaml") == spinfile
        assert cli.find_spinfile("SPIN_TEST_CLI_DOESNOTEXIST") is None
        assert cli.find_spinfile(spinfile=None) == spinfile


def test_load_plugin(cfg: ConfigTree, caplog: LogCaptureFixture) -> None:
    """
    spin.cli.load_plugin loads valid plugins into the tree if they're not
    already present
    """
    # TODO: Maybe test to add a package that ships unloaded requirements.

    from types import ModuleType

    caplog.set_level(logging.DEBUG)

    # load plugin that is already present in the tree
    plugin = cli.load_plugin(cfg, "spin.builtin")
    assert isinstance(plugin, ModuleType)
    assert "import plugin spin.builtin" in caplog.text
    assert "add subtree" not in caplog.text

    # load plugin that is not present in the tree
    assert not cfg.loaded.get("pytest")
    plugin = cli.load_plugin(cfg=cfg, import_spec="pytest")
    assert isinstance(plugin, ModuleType)
    assert "import plugin pytest" in caplog.text
    assert "add subtree pytest" in caplog.text
    assert cfg.loaded.get("pytest")
    assert isinstance(plugin.defaults, ConfigTree)
    assert plugin.defaults == ConfigTree({"_requires": []})

    # load plugin that does not exist
    with pytest.raises(ModuleNotFoundError, match="No module named 'foo"):
        cli.load_plugin(cfg, import_spec="foo")


def test_reverse_toposort(cfg: ConfigTree) -> None:
    """
    spin.cli.reverse_toposort returns a list containing the passed 'nodes' in
    the expected order while failing when passing cycles
    """
    graph = {
        "spin.builtin": ["spin.builtin.shell"],
        "spin.builtin.shell": ["spin.builtin.cache"],
        "spin.builtin.cache": [],
    }
    result = cli.reverse_toposort(nodes=graph.keys(), graph=graph)

    # Ensure that the origin graph is not modified by calling reverse_toposort.
    assert graph == {
        "spin.builtin": ["spin.builtin.shell"],
        "spin.builtin.shell": ["spin.builtin.cache"],
        "spin.builtin.cache": [],
    }

    assert result == ["spin.builtin.cache", "spin.builtin.shell", "spin.builtin"]

    graph = {"foo": ["bar"], "bar": ["foo"]}
    with pytest.raises(click.Abort, match="dependency graph has at least one cycle"):
        cli.reverse_toposort(nodes=graph.keys(), graph=graph)


def test_base_options() -> None:
    """spin.cli.base_options can be used to equip functions with defined"""

    def command() -> None:
        return "hello earth"

    decorated_command = cli.base_options(command)
    assert isinstance(decorated_command, Callable)
    assert vars(decorated_command).get("__click_params__")

    click_options = vars(decorated_command)["__click_params__"]
    expected_options = (
        "version",
        "help",
        "cwd",
        "envbase",
        "spinfile",
        "quiet",
        "verbose",
        "debug",
        "properties",
        "provision",
        "cleanup",
    )
    assert len(click_options) == len(expected_options)
    assert all(option in str(click_options) for option in expected_options)
    assert command() == "hello earth"  # check if command is still callable


def test_group_with_aliases() -> None:
    """
    spin.cli.GroupWithAliases is able to assign new command aliases and return
    existing ones
    """
    grouper = cli.GroupWithAliases()
    assert not grouper._aliases  # pylint: disable=protected-access

    def command() -> None:
        pass

    cmd = click.command(command)
    grouper.register_alias(alias="foo", cmd_object=cmd)
    assert grouper._aliases == {"foo": cmd}  # pylint: disable=protected-access

    with click.Context(cmd) as ctx:
        assert grouper.get_command(ctx=ctx, cmd_name="foo") is cmd


def test_find_plugin_packages(cfg: ConfigTree) -> None:
    """
    spin.cli.find_plugin_packages returns a generator which items are the
    expected 'plugin-packages' of the passed configuration tree
    """
    result = cli.find_plugin_packages(cfg)
    assert isinstance(result, Generator)
    assert not list(result), "Result should not have length > 0"

    packages = ["flake8", "pytest"]
    cfg["plugin-packages"] = packages
    assert list(cli.find_plugin_packages(cfg)) == packages


def test_yield_plugin_import_specs(cfg: ConfigTree) -> None:
    """spin.cli.yield_plugin_import_specs returns the expected plugins"""
    result = cli.yield_plugin_import_specs(cfg)

    assert isinstance(result, Generator)
    assert not list(result), "Result should not have length > 0"

    cfg["plugins"] = ["foo"]
    assert list(cli.yield_plugin_import_specs(cfg)) == ["foo"]

    cfg["plugins"] = [{"foo": ["bar", "baz"]}]
    assert list(cli.yield_plugin_import_specs(cfg)) == ["foo.bar", "foo.baz"]

    cfg["plugins"] = [{"foo": ["bar", "baz"]}, "buz"]
    assert list(cli.yield_plugin_import_specs(cfg)) == ["foo.bar", "foo.baz", "buz"]


def test_load_config_tree_basic(
    mocker: MockerFixture,
    tmp_path: PathlibPath,
    minimum_yaml_path: str,
    caplog: LogCaptureFixture,
) -> None:
    """
    spin.cli.load_config_tree returns a valid configuration tree with all
    expected attributes set (verbose)
    """
    mock_toporun = mocker.patch("spin.cli.toporun")
    mock_click_echo = mocker.patch("click.echo")
    caplog.set_level(logging.DEBUG)
    with chdir(tmp_path):
        spinfile = tmp_path / "spinfile.yaml"
        copy(minimum_yaml_path, spinfile)

        cfg = cli.load_config_tree(spinfile=spinfile, envbase=tmp_path, quiet=True)

        assert not cfg.verbose
        assert not cfg.cleanup
        assert not cfg.provision
        assert cfg.quiet
        assert cfg.quietflag == "-q"
        assert cfg.spin.spinfile == Path(spinfile)
        assert cfg.spin.project_root == os.path.normcase(os.path.dirname(spinfile))
        assert cfg.spin.project_name == os.path.basename(tmp_path)
        assert cfg.spin.plugin_dir == Path(tmp_path / "plugins")
        assert cfg.spin.plugin_dir in sys.path
        assert cfg.spin.env_base == Path(tmp_path)

        assert os.path.isfile(tmp_path / ".spin" / ".gitignore")
        with open(tmp_path / ".spin" / ".gitignore", "r", encoding="utf-8") as f:
            assert f.read() == "# Created by spin automatically\n*\n"
        mock_click_echo.assert_not_called()

        assert isinstance(cfg.loaded, ConfigTree)
        assert cfg.loaded.get("spin.builtin")
        assert len(cfg.loaded) == 1  # no other/global plugins loaded
        mock_toporun.assert_called_once()

        assert cfg.get("plugin-path") is None
        assert f"Loading {spinfile}" in caplog.text
        assert "loading project plugins:" in caplog.text
        assert "  import plugin spin.builtin" in caplog.text
        assert "  add subtree builtin" in caplog.text
        assert "loading global plugins:" in caplog.text


def test_load_config_tree_extended(
    mocker: MockerFixture,
    tmp_path: PathlibPath,
    minimum_yaml_path: str,
    caplog: LogCaptureFixture,
) -> None:
    """
    spin.cli.load_config_tree returns a valid configuration tree with all
    expected attributes set (quiet + provision)
    """
    mock_echo = mocker.patch("spin.echo")
    caplog.set_level(logging.DEBUG)
    with chdir(tmp_path):
        spinfile = tmp_path / "spinfile.yaml"
        copy(minimum_yaml_path, spinfile)

        cfg = cli.load_config_tree(
            spinfile=spinfile,
            envbase=tmp_path,
            cwd=tmp_path,
            verbose=True,
            cleanup=True,
            provision=True,
            properties=("foo=bar",),
        )

        assert not cfg.quiet
        assert cfg.verbose
        assert cfg.provision
        assert cfg.foo == "bar"
        assert cfg.cleanup
        assert cfg.quietflag is None
        assert cfg.spin.spinfile == Path(spinfile)
        assert cfg.spin.project_root == os.path.normcase(os.path.dirname(spinfile))
        assert cfg.spin.project_name == os.path.basename(tmp_path)
        assert cfg.spin.plugin_dir == Path(tmp_path / "plugins")
        assert cfg.spin.plugin_dir in sys.path
        assert cfg.spin.env_base == Path(tmp_path)

        assert os.path.isfile(tmp_path / ".spin" / ".gitignore")
        with open(tmp_path / ".spin" / ".gitignore", "r", encoding="utf-8") as f:
            assert f.read() == "# Created by spin automatically\n*\n"
        mock_echo.assert_called_with("mkdir", ".spin")

        assert isinstance(cfg.loaded, ConfigTree)
        assert cfg.loaded.get("spin.builtin")
        assert len(cfg.loaded) == 1  # no other/global plugins loaded
        assert cfg.get("plugin-path") is None
        assert f"Loading {spinfile}" in caplog.text
        assert "loading project plugins:" in caplog.text
        assert "  import plugin spin.builtin" in caplog.text
        assert "  add subtree builtin" in caplog.text
        assert "loading global plugins:" in caplog.text


def test_load_config_tree_no_minimum_spin(tmp_path: PathlibPath) -> None:
    """spin.cli.load_config_tree will fail if no minimum-spin is set"""
    spinfile = tmp_path / "spinfile.yaml"
    with open(spinfile, "w", encoding="utf-8") as f:
        f.write("\nspin:\n spin_global: ")

    with pytest.raises(click.Abort, match=".*spin requires 'minimum-spin' to be set"):
        cli.load_config_tree(spinfile=spinfile, envbase=tmp_path)


def test_load_config_tree_incompatible_spin_version(tmp_path: PathlibPath) -> None:
    """
    spin.cli.load_config_tree will fail if the spin version required by the
    spinfile is not being used to build the tree
    """
    spinfile = tmp_path / "spinfile.yaml"
    with open(spinfile, "w", encoding="utf-8") as f:
        f.write("minimum-spin: 9999\nspin:\n spin_global: ")

    with pytest.raises(click.Abort, match=".*this project requires spin>=9999"):
        cli.load_config_tree(spinfile=spinfile, envbase=tmp_path)


def test_install_plugin_packages(
    mocker: MockerFixture,
    cfg: ConfigTree,
    tmp_path: PathlibPath,
) -> None:
    """
    spin.cli.install_plugin_packages executes the required commands to install
    plugin and dev packages
    """
    mocker.patch.dict(os.environ, {"PYTHONPATH": os.path.sep + "python"})
    mocker.patch("spin.cli.glob.iglob", return_value=("foo.egg-link", "bar.egg-link"))
    mocker.patch(
        "spin.cli.readtext",
        side_effect=("foo.egg-link-content", "bar.egg-link-content"),
    )
    mock_sh = mocker.patch("spin.cli.sh")

    cfg.spin.plugin_dir = Path(tmp_path / "plugins")
    cfg.spin.extra_index = "https://packages.contact.de/apps/16.0"
    cfg["plugin-packages"] = ["foo", "bar"]

    assert not os.path.isdir(Path(tmp_path / "plugins"))
    cli.install_plugin_packages(cfg)
    assert os.path.isdir(Path(tmp_path / "plugins"))
    assert "'--extra-index-url', 'https://packages.contact.de/apps/16.0', 'foo'" in str(
        mock_sh.call_args_list[0]
    )
    assert "'--extra-index-url', 'https://packages.contact.de/apps/16.0', 'bar'" in str(
        mock_sh.call_args_list[1]
    )
    assert len(mock_sh.call_args_list) == 2

    # check if the path was reset
    assert os.getenv("PYTHONPATH") == os.path.sep + "python"

    with open(tmp_path / "plugins" / "easy-install.pth", "r", encoding="utf-8") as f:
        assert f.read() == "foo.egg-link-content\nbar.egg-link-content"

    # also check if the the path was removed in case it did not exist before
    del os.environ["PYTHONPATH"]
    cli.install_plugin_packages(cfg)
    assert not os.getenv("PYTHONPATH")
