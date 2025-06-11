# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/


import subprocess


def execute_spin_in_clean_and_provisioned_env(
    yaml, env, path="tests/integration/yamls", cmd=""
):
    """Helper function to execute spin and return the output"""
    subprocess.check_call(
        f"spin -p spin.data={env} -C {path} --env {str(env)} -f {yaml} cleanup".split(
            " "
        )
    )
    subprocess.check_call(
        f"spin -p spin.data={env} -C {path} --env {str(env)} -f {yaml} provision".split(
            " "
        )
    )
    return subprocess.check_output(
        f"spin -p spin.data={env} -C {path} --env {str(env)} -f {yaml} {cmd}".split(
            " "
        ),
        encoding="utf-8",
        stderr=subprocess.PIPE,
    ).strip()


def test_complex_plugin_dependencies(tmp_path):
    """
    spin is able to handle plugin-packages with plugins that depend on each
    other - within a plugin package and across multiple plugin-packages.
    """
    output = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        yaml="complex_plugin_dependencies.yaml",
        cmd="depend",
    )
    assert "spin: This is spin's depend plugin" in output


def test_schemadoc_spin_only(tmp_path):
    """Ensuring that the schemadoc task is able to only document spins schema"""
    output = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        path="tests/yamls",
        yaml="sample.yaml",
        cmd="-q schemadoc --rst --full=False",
    )
    # just to name a few:
    assert ".. py:data:: spin.spinfile" in output
    assert ".. py:data:: spin.project_root" in output
    assert "The schema shipped by spin." in output


def test_schemadoc_spin_only_cli_output(tmp_path):
    """Ensuring that the schemadoc task is able to only document spins schema"""
    output = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        path="tests/yamls",
        yaml="sample.yaml",
        cmd="-q schemadoc --full=False",
    )
    # just to name a few:
    assert "spin.spinfile: [path] = 'spinfile.yaml'" in output
    assert "spin.project_root: [path, internal]" in output


def test_schemadoc_selection_single(tmp_path):
    """Check that an individual property without a parent can be accessed"""
    output = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        path="tests/yamls",
        yaml="sample.yaml",
        cmd="-q schemadoc --rst --full=False plugins",
    )
    assert output.startswith(".. py:data:: plugins")
    assert output.endswith("The list of plugins to import.")


def test_schemadoc_selection_single_cli_output(tmp_path):
    """Check that an individual property without a parent can be accessed"""
    output = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        path="tests/yamls",
        yaml="sample.yaml",
        cmd="-q schemadoc --full=False verbosity",
    )
    assert output.startswith("verbosity: [str, internal] = 'NORMAL'")
    assert output.endswith("Levels are: QUIET, NORMAL, INFO, DEBUG")


def test_schemadoc_selection_nested(tmp_path):
    """
    Validating that nested properties can be accessed using the schemadoc task.
    """
    output = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        path="tests/yamls",
        yaml="sample.yaml",
        cmd="-q schemadoc --rst --full=False spin.spinfile",
    )
    assert output.startswith(".. py:data:: spin.spinfile")
    assert output.endswith("be overridden via 'spin -f <filename>'.")


def test_schemadoc_full_param(tmp_path):
    """
    Checking schemadoc full param.
    """
    output = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        path="tests/yamls",
        yaml="csspin_dummy_config.yaml",
        cmd="-q schemadoc --rst --full=False",
    )
    assert "dummy" not in output
    assert "dummy.dummy" not in output

    output = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        path="tests/yamls",
        yaml="csspin_dummy_config.yaml",
        cmd="-q schemadoc --rst --full=True",
    )
    assert "dummy" in output
    assert "dummy.dummy" in output


def test_system_provision(tmp_path):
    """
    Validate that system_provision task is working properly.
    """
    output_debian = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        yaml="system_provision.yaml",
        cmd="system-provision debian",
    )
    assert "apt install -y " in output_debian
    assert "git" in output_debian
    output_windows = execute_spin_in_clean_and_provisioned_env(
        env=tmp_path,
        yaml="system_provision.yaml",
        cmd="system-provision windows",
    )
    assert "choco install -y " in output_windows
    assert "git" in output_windows
