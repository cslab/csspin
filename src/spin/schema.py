# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/
#
# Disabling the mypy override rule, since it's suggestions are not that useful
# for this module.
# mypy: disable-error-code=override

"""
Module defining classes for handling schemas and descriptors for types of data
used within the package. Schemas describe the structure and properties of data
objects, while descriptors define how to coerce values and retrieve default
values for specific data types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from path import Path

from spin import tree

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable, Type


class SchemaError(TypeError):
    pass


class BaseDescriptor:
    """
    Base class for descriptors providing methods for coercion and getting
    default values.
    """

    def __init__(self: BaseDescriptor, description: dict | tree.ConfigTree) -> None:
        self._keyinfo = None
        for key, value in description.items():
            setattr(self, key, value)
            if key == "default":
                self._keyinfo = tree.tree_keyinfo(description, key)  # type: ignore[arg-type]

    def coerce(self: BaseDescriptor, value: Any) -> Any:
        return value

    def get_default(self: BaseDescriptor, defaultdefault: Any = None) -> Any:
        val = getattr(self, "default", defaultdefault)
        if val is not None:
            val = self.coerce(val)
        return val


DESCRIPTOR_REGISTRY = {}


def descriptor(tag: str) -> Callable:
    def decorator(cls: Type[BaseDescriptor]) -> None:
        DESCRIPTOR_REGISTRY[tag] = cls

    return decorator


@descriptor("path")
class PathDescriptor(BaseDescriptor):
    """Descriptor for handling file paths, coercing values to Path objects."""

    def coerce(self: PathDescriptor, value: str | None) -> Path | None:
        if value is not None:
            return Path(value)
        return value


@descriptor("str")
class StringDescriptor(BaseDescriptor):
    """Descriptor for handling string values."""

    def coerce(self: StringDescriptor, value: str) -> str:
        return str(value)


@descriptor("boolean")
class BoolDescriptor(BaseDescriptor):
    """Descriptor for handling boolean values."""

    def coerce(self: BoolDescriptor, value: Any) -> bool:
        return bool(value)

    def get_default(self: BoolDescriptor) -> bool:  # pylint: disable=arguments-differ
        return super().get_default(False)  # type: ignore[no-any-return]


@descriptor("list")
class ListDescriptor(BaseDescriptor):
    """
    Descriptor for handling lists, splitting string values and coercing them to
    lists.
    """

    def coerce(self: ListDescriptor, value: Iterable) -> list:
        if isinstance(value, str):
            value = value.split()
        return list(value)

    def get_default(self: ListDescriptor) -> list:  # pylint: disable=arguments-differ
        return super().get_default([])  # type: ignore[no-any-return]


@descriptor("object")
class ObjectDescriptor(BaseDescriptor):
    """
    Descriptor for handling nested objects, recursively building descriptors for
    properties.
    """

    def __init__(self: ObjectDescriptor, description: dict) -> None:
        super().__init__(description)
        if not hasattr(self, "properties"):
            self.properties = tree.ConfigTree()
        for key, value in self.properties.items():
            ki = tree.tree_keyinfo(self.properties, key)
            odesc = build_descriptor(value)
            self.properties[key] = odesc
            if odesc._keyinfo is None:
                odesc._keyinfo = ki

    def get_default(  # pylint: disable=arguments-differ
        self: ObjectDescriptor,
    ) -> tree.ConfigTree:
        data = super().get_default(tree.ConfigTree())
        for key, desc in self.properties.items():
            data[key] = desc.get_default()
            # pylint: disable=protected-access
            if desc._keyinfo:
                tree.tree_set_keyinfo(data, key, desc._keyinfo)
        data._ConfigTree__schema = self  # pylint: disable=protected-access
        return data  # type: ignore[no-any-return]

    def coerce(self: ObjectDescriptor, value: dict) -> dict:
        if not isinstance(value, dict):
            raise SchemaError("dictionary required")
        return value


def build_descriptor(description: dict) -> Type[BaseDescriptor]:
    description["type"] = description.get("type", "object").split()
    factory = DESCRIPTOR_REGISTRY.get(description["type"][0])
    if factory is None:
        raise SchemaError(f"No factory for '{description['type'][0]}'")
    return factory(description)  # type: ignore[return-value]


def schema_load(fn: str) -> Type[BaseDescriptor]:
    props = tree.tree_load(fn)
    return build_schema(props)


def build_schema(props: tree.ConfigTree) -> Type[BaseDescriptor]:
    desc = {"type": "object", "properties": props}
    return build_descriptor(desc)
