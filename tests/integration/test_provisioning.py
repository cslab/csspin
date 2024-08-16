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


def test_schemadoc_spin_only(tmpdir):
    """Ensuring that the schemadoc task is able to only document spins schema"""
    output = execute_spin(
        tmpdir=tmpdir,
        path="tests/yamls",
        what="sample.yaml",
        cmd="-q schemadoc --full=False",
    )
    # just to name a few:
    assert ".. py:data:: spin.spinfile" in output
    assert ".. py:data:: spin.project_root" in output
    assert output.endswith("The schema shipped by cs.spin.")


def test_schemadoc_selection_single(tmpdir):
    """Check that an individual property without a parent can be accessed"""
    output = execute_spin(
        tmpdir=tmpdir,
        path="tests/yamls",
        what="sample.yaml",
        cmd="-q schemadoc --full=False plugins",
    )
    assert output.startswith(".. py:data:: plugins")
    assert output.endswith("The list of plugins to import.")


def test_schemadoc_selection_nested(tmpdir):
    """
    Validating that nested properties can be accessed using the schemadoc task.
    """
    output = execute_spin(
        tmpdir=tmpdir,
        path="tests/yamls",
        what="sample.yaml",
        cmd="-q schemadoc --full=False spin.spinfile",
    )
    assert output.startswith(".. py:data:: spin.spinfile")
    assert output.endswith("be overridden via 'spin -f <filename>'.")
