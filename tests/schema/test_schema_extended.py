# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import subprocess
from os import environ

import pytest

from spin import backtick


def test_testplugin_general(cfg, tmpdir) -> None:
    """
    Using a test plugin named "testplugin" that uses lots of data types and
    interpolation to validate the enforcement of the schema.
    """
    output = backtick(
        f"spin -q -C tests/schema --env {tmpdir} -f test_schema_general.yaml "
        "--provision testplugin"
    )
    output = output.strip()
    print(output)


@pytest.mark.wip()
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
        subprocess.check_output(
            [
                "spin",
                "-C",
                "tests/schema",
                "--env",
                str(tmp_path),
                "-f",
                "test_schema_general.yaml",
                "--provision",
                "-p",
                property_value,
            ],
            encoding="utf-8",
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        assert f"Can't override internal property {property_value}" in exc.stderr
    else:
        pytest.fail("Failing since internal property was overridden.")


@pytest.mark.wip()
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
        subprocess.check_output(
            [
                "spin",
                "-C",
                "tests/schema",
                "--env",
                str(tmp_path),
                "-f",
                "test_schema_general.yaml",
                "--provision",
            ],
            encoding="utf-8",
            stderr=subprocess.PIPE,
            env=environ | {envvar: envvar_value},
        )
    except subprocess.CalledProcessError as exc:
        assert (
            f"Can't override internal property {property}={envvar_value}" in exc.stderr
        )
    else:
        pytest.fail("Failing since internal property was overridden.")
