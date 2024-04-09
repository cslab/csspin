# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/
# pylint: disable=protected-access

"""Module implementing tests regarding schemas and descriptors."""

from typing import Callable

from pytest import raises

from spin import config, schema
from spin.schema import DESCRIPTOR_REGISTRY


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
                properties=config(a=config(type="path")),
            ),
        )
    )

    config_tree = test_schema.get_default()
    assert config_tree._ConfigTree__parentinfo is None
    assert config_tree._ConfigTree__schema is test_schema
    assert config_tree.subtree._ConfigTree__schema is test_schema.properties["subtree"]

    config_tree.x = "a b c"
    assert config_tree.x == ["a", "b", "c"]
    with raises(TypeError, match="'int' object is not iterable"):
        config_tree.x = 12
    assert config_tree.x == ["a", "b", "c"]
    config_tree.subtree.a = "file"
    assert repr(config_tree.subtree.a) == "Path('file')"

    with raises(schema.SchemaError, match="dictionary required"):
        config_tree.subtree = "Oops that did not work!"


def test_schema_invalid_factory() -> None:
    """
    Function ensuring that not implemented factories will raise SchemaError.
    """
    with raises(schema.SchemaError, match="No factory for 'set'"):
        schema.build_schema(config(x=config(type="set")))


def test_descriptor() -> None:
    """Test checking the registration of a descriptor."""
    from spin.schema import BaseDescriptor  # pylint: disable=unused-import

    assert "test" not in DESCRIPTOR_REGISTRY

    @schema.descriptor("test")
    class TestDescriptor(BaseDescriptor):  # pylint: disable=unused-variable
        """Test class"""

    assert "test" in DESCRIPTOR_REGISTRY
    assert isinstance(DESCRIPTOR_REGISTRY["test"], Callable)  # type: ignore[arg-type]
    del DESCRIPTOR_REGISTRY["test"]
    assert "test" not in DESCRIPTOR_REGISTRY


def test_registered_descriptors() -> None:
    """Test checking if all expected descriptors are registered successfully."""

    assert isinstance(DESCRIPTOR_REGISTRY, dict)
    assert "path" in DESCRIPTOR_REGISTRY
    assert "str" in DESCRIPTOR_REGISTRY
    assert "boolean" in DESCRIPTOR_REGISTRY
    assert "object" in DESCRIPTOR_REGISTRY
    assert "list" in DESCRIPTOR_REGISTRY
    assert len(DESCRIPTOR_REGISTRY.keys()) == 5


def test_build_descriptor() -> None:
    """Function testing the build of a descriptor to generate a schema."""

    assert isinstance(
        schema.build_descriptor(description={}), DESCRIPTOR_REGISTRY["object"]
    )
    assert isinstance(
        schema.build_descriptor(description={"type": "object"}),
        DESCRIPTOR_REGISTRY["object"],
    )
    assert isinstance(
        schema.build_descriptor(description={"type": "path"}),
        DESCRIPTOR_REGISTRY["path"],
    )
    assert isinstance(
        schema.build_descriptor(description={"type": "str"}), DESCRIPTOR_REGISTRY["str"]
    )
    assert isinstance(
        schema.build_descriptor(description={"type": "boolean"}),
        DESCRIPTOR_REGISTRY["boolean"],
    )
    assert isinstance(
        schema.build_descriptor(description={"type": "list"}),
        DESCRIPTOR_REGISTRY["list"],
    )
