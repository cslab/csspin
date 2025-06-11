# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/
# pylint: disable=protected-access

"""Module implementing tests regarding schemas and descriptors."""

from typing import Callable

from click import Abort as click_abort
from pytest import raises

from csspin import config, schema
from csspin.schema import DESCRIPTOR_REGISTRY


def test_build_schema() -> None:
    """
    Function that builds a schema for testing the expected default values as
    well as assigning values to check how the config tree behaves on that.
    """
    test_schema = schema.build_schema(
        config(
            x=config(type="list"),
            subtree=config(
                type="object",
                properties=config(
                    a=config(type="list"),
                    b=config(type="int"),
                ),
            ),
        )
    )

    config_tree = test_schema.get_default()
    assert config_tree._ConfigTree__parentinfo is None
    assert config_tree._ConfigTree__schema is test_schema
    assert config_tree.subtree._ConfigTree__schema is test_schema.properties["subtree"]

    assert hasattr(config_tree, "x")
    assert hasattr(config_tree, "subtree")
    assert hasattr(config_tree.subtree, "a")
    assert hasattr(config_tree.subtree, "b")

    config_tree.x = "a b c"
    assert config_tree.x == "a b c"


def test_schema_invalid_factory() -> None:
    """
    Function ensuring that not implemented factories will raise SchemaError.
    """
    with raises(click_abort, match="Unknown type 'set' found in schema configuration."):
        schema.build_schema(config(x=config(type="set")))


def test_descriptor() -> None:
    """Test checking the registration of a descriptor."""
    from csspin.schema import BaseDescriptor  # pylint: disable=unused-import

    assert "test" not in DESCRIPTOR_REGISTRY

    @schema.descriptor("test")
    class TestDescriptor(BaseDescriptor):  # pylint: disable=unused-variable
        """Test class"""

    assert "test" in DESCRIPTOR_REGISTRY
    assert isinstance(DESCRIPTOR_REGISTRY["test"], Callable)  # type: ignore[arg-type]
    del DESCRIPTOR_REGISTRY["test"]
    assert "test" not in DESCRIPTOR_REGISTRY


def test_build_descriptor() -> None:
    """Function testing the build of a descriptor to generate a schema."""

    assert isinstance(
        schema.build_descriptor(description={}), DESCRIPTOR_REGISTRY["object"]
    )
    for kind in ("object", "list", "path", "str", "float", "int", "bool"):
        assert isinstance(
            schema.build_descriptor(description={"type": kind}),
            DESCRIPTOR_REGISTRY[kind],
        )
