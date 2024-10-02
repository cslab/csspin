# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import subprocess
from os import environ

import pytest


def execute_spin(yaml, env, cmd="", subprocess_env=None):
    """Helper function to execute spin and return the output"""
    cmd = (f"spin -C tests/schema --env {str(env)} -f {yaml} " + cmd).split(" ")
    print(subprocess.list2cmdline(cmd))
    return subprocess.check_output(
        cmd,
        encoding="utf-8",
        stderr=subprocess.PIPE,
        env=subprocess_env,
    ).strip()


def test_testplugin_general(cfg, tmp_path) -> None:
    """
    Using a test plugin named "testplugin" that uses lots of data types and
    interpolation to validate the enforcement of the schema.
    """
    execute_spin(
        yaml="test_schema_general.yaml",
        env=tmp_path,
        cmd="provision",
    )
    execute_spin(
        yaml="test_schema_general.yaml",
        env=tmp_path,
        cmd="testplugin",
    )


def test_environment_set_via_spinfile(tmp_path) -> None:
    """
    Ensuring that environment variables can be set and unset via spinfile.yaml
    """
    output = execute_spin(
        yaml="test_schema_environment.yaml",
        env=tmp_path,
        cmd="provision",
    )
    assert "spin: set FOO=bar" in output
    assert "spin: unset BAR" in output


@pytest.mark.parametrize(
    "property_value",
    [
        pytest.param("testplugin.internal_property=."),
        pytest.param("spin.project_root=."),
    ],
)
def test_schema_failure_override_internal_via_cli(
    property_value,
    tmp_path,
) -> None:
    """
    Ensuring that internal marked properties can't be modified by using the
    options via command-line.
    """
    try:
        execute_spin(
            yaml="test_schema_general.yaml",
            env=tmp_path,
            cmd=f"-p {property_value} provision",
        )
    except subprocess.CalledProcessError as exc:
        assert f"Can't override internal property {property_value}" in exc.stderr
    else:
        pytest.fail("Failing since internal property was overridden.")


@pytest.mark.parametrize(
    "envvar,property,envvar_value",
    [
        pytest.param(
            "SPIN_TREE_TESTPLUGIN__INTERNAL_PROPERTY",
            "testplugin.internal_property",
            ".",
        ),
        pytest.param("SPIN_TREE_SPIN__PROJECT_ROOT", "spin.project_root", "."),
    ],
)
def test_schema_failure_override_internal_via_environment(
    envvar,
    property,
    envvar_value,
    tmp_path,
) -> None:
    """
    Ensuring that internal marked properties can't be modified by using the
    options via environment variables.
    """
    try:
        execute_spin(
            yaml="test_schema_general.yaml",
            env=tmp_path,
            cmd="provision",
            subprocess_env=environ | {envvar: envvar_value},
        )
    except subprocess.CalledProcessError as exc:
        assert (
            f"Can't override internal property {property}={envvar_value}" in exc.stderr
        )
    else:
        pytest.fail("Failing since internal property was overridden.")
