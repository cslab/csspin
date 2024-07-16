# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import pytest

from spin import backtick


@pytest.fixture(autouse=True)
def cfg(cfg):
    """Using the minimal configuration tree"""


def execute_spin(tmpdir, what, cmd, path="tests/integration/yamls", props=""):
    output = backtick(
        f"spin -p spin.cache={tmpdir} {props} -C {path} --env {tmpdir} -f"
        f" {what} --cleanup --provision {cmd}"
    )
    output = output.strip()
    return output


def test_complex_plugin_dependencies(tmpdir):
    """
    spin is able to handle plugin-packages with plugins that depend on each
    other - within a plugin package and across multiple plugin-packages.
    """
    output = execute_spin(
        tmpdir=tmpdir,
        what="complex_plugin_dependencies.yaml",
        cmd="depend",
    )
    assert "spin: This is spin's depend plugin" in output
