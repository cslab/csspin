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

from spin import get_tree
from spin.cli import load_config_tree

if TYPE_CHECKING:
    import pathlib
    from spin.tree import ConfigTree

from path import Path


@fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


@fixture()
def cfg() -> ConfigTree:
    load_config_tree("tests/yamls/none.yaml", cwd=os.getcwd())
    return get_tree()


@fixture()
def cfg_spin_dummy() -> ConfigTree:
    load_config_tree("tests/yamls/spin_dummy_config.yaml", cwd=os.getcwd())
    return get_tree()


@fixture()
def minimum_yaml_path() -> str:
    return os.path.join(os.path.dirname(__file__), "yamls", "none.yaml")


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
    try:
        cwd = os.getcwd()
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
    return Path(os.path.dirname(__file__)) / "data" / "trivial"
