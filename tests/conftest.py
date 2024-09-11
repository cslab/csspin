# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""Module implementing fixtures used in unit tests."""

from __future__ import annotations

import contextlib
import os
from typing import TYPE_CHECKING

from click.testing import CliRunner
from pytest import fixture

from spin.cli import load_config_tree

if TYPE_CHECKING:
    import pathlib
    from spin.tree import ConfigTree

from path import Path


@fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


@fixture()
def cfg(minimum_yaml_path) -> ConfigTree:
    return load_config_tree(minimum_yaml_path, cwd=os.getcwd())


@fixture()
def cfg_spin_dummy() -> ConfigTree:
    return load_config_tree("tests/yamls/spin_dummy_config.yaml", cwd=os.getcwd())


@fixture()
def minimum_yaml_path() -> str:
    return Path(__file__).dirname() / "yamls" / "sample.yaml"


@fixture()
def tmp_path(tmp_path: pathlib.Path):
    """
    Using the custom Path provides simplifies tests, since cs.spin is using this
    type a lot.
    """
    return Path(tmp_path)


@contextlib.contextmanager
def chdir(path):
    """A contextmanager which changes the cwd and returns to
    the original cwd on exit
    """
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


@fixture(scope="session", autouse=True)
def disable_global_yaml():
    if not os.environ.get("CI"):
        os.environ["SPIN_DISABLE_GLOBAL_YAML"] = "True"


@fixture()
def trivial_plugin_path() -> Path:
    return Path(__file__).dirname() / "data" / "trivial"


@fixture(scope="session")
def directive_spinfile() -> Path:
    return load_config_tree(
        Path(__file__).dirname()
        / "integration"
        / "directives"
        / "fixtures"
        / "spinfile.yaml",
        cwd=os.getcwd(),
    )
