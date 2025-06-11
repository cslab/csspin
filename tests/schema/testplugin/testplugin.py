# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""A Plugin used for testing the schema and type checking"""

import os

from path import Path

from csspin import (
    config,
    confirm,
    debug,
    echo,
    error,
    info,
    interpolate1,
    setenv,
    task,
    warn,
)

defaults = config(
    nested_properties=config(
        iam_a_path="path1",
        iam_another_path="path2",
    ),
    integer_property=1,
    float_property=1.0,
    string_property="string",
    path_property=Path(os.getcwd()),
    list_property=["item1", "item2", "item3"],
    int_to_interpolate="{testplugin.integer_property}",
    path_to_interpolate=Path("{testplugin.path_property}"),
    list_to_interpolate=[
        "{testplugin.path_to_interpolate}",
        "{testplugin.integer_property}",
        "{testplugin.float_property}",
        "static",
    ],
    bool_property=True,
    bool_to_interpolate="{SPIN_TESTING_SCHEMA_VALIDATION_TOGGLE}",
    internal_property="internal",
)


def configure(cfg) -> None:
    setenv(SPIN_TESTING_SCHEMA_VALIDATION_TOGGLE=True)
    cfg.testplugin.another_secret_property = "sssssshhhitsasecret"


@task()
def testplugin(cfg) -> None:
    cwd = Path(os.getcwd())

    assert cfg.testplugin.bool_property is True
    assert cfg.testplugin.bool_to_interpolate is True
    assert cfg.testplugin.integer_property == cfg.testplugin.int_to_interpolate == 1
    assert cfg.testplugin.float_property == 1.0
    assert (
        cfg.testplugin.string_property
        == interpolate1("{testplugin.string_property}")
        == "string"
    )
    assert (
        cfg.testplugin.path_property
        == Path(interpolate1("{testplugin.path_property}"))
        == cwd
    )
    assert cfg.testplugin.list_property == ["item1", "item2", "item3"]
    assert (
        cfg.testplugin.path_to_interpolate
        == Path(interpolate1("{testplugin.path_to_interpolate}"))
        == cfg.testplugin.path_property
        == cwd
    )
    assert cfg.testplugin.list_to_interpolate == [str(cwd), "1", "1.0", "static"]
    assert isinstance(cfg.testplugin.nested_properties.iam_another_path, Path)
    assert cfg.testplugin.nested_properties.iam_another_path == Path("iam_another_path")
    assert isinstance(cfg.testplugin.nested_properties.iam_a_path, Path)
    assert cfg.testplugin.nested_properties.iam_a_path == Path("path1")


@task()
def output_secrets(cfg) -> None:
    debug(cfg.testplugin.secret_property)
    echo(cfg.testplugin.secret_property)
    info(cfg.testplugin.secret_property)
    warn(cfg.testplugin.secret_property)
    error(cfg.testplugin.secret_property)
    confirm(cfg.testplugin.secret_property)
