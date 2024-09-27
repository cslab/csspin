# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/


import subprocess


def execute_spin(yaml, env, path="tests/integration/yamls", cmd=""):
    """Helper function to execute spin and return the output"""
    return subprocess.check_output(
        (
            f"spin -p spin.data={env} -C {path} --env {str(env)} -f {yaml} --cleanup"
            " --provision "
            + cmd
        ).split(" "),
        encoding="utf-8",
        stderr=subprocess.PIPE,
    ).strip()


def test_complex_plugin_dependencies(tmp_path):
    """
    spin is able to handle plugin-packages with plugins that depend on each
    other - within a plugin package and across multiple plugin-packages.
    """
    output = execute_spin(
        env=tmp_path,
        yaml="complex_plugin_dependencies.yaml",
        cmd="depend",
    )
    assert "spin: This is spin's depend plugin" in output


def test_schemadoc_spin_only(tmp_path):
    """Ensuring that the schemadoc task is able to only document spins schema"""
    output = execute_spin(
        env=tmp_path,
        path="tests/yamls",
        yaml="sample.yaml",
        cmd="-q schemadoc --full=False",
    )
    # just to name a few:
    assert ".. py:data:: spin.spinfile" in output
    assert ".. py:data:: spin.project_root" in output
    assert output.endswith("The schema shipped by cs.spin.")


def test_schemadoc_selection_single(tmp_path):
    """Check that an individual property without a parent can be accessed"""
    output = execute_spin(
        env=tmp_path,
        path="tests/yamls",
        yaml="sample.yaml",
        cmd="-q schemadoc --full=False plugins",
    )
    assert output.startswith(".. py:data:: plugins")
    assert output.endswith("The list of plugins to import.")


def test_schemadoc_selection_nested(tmp_path):
    """
    Validating that nested properties can be accessed using the schemadoc task.
    """
    output = execute_spin(
        env=tmp_path,
        path="tests/yamls",
        yaml="sample.yaml",
        cmd="-q schemadoc --full=False spin.spinfile",
    )
    assert output.startswith(".. py:data:: spin.spinfile")
    assert output.endswith("be overridden via 'spin -f <filename>'.")
