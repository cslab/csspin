# -*- mode: python; coding: utf-8 -*-
#
# Copyright 2020 CONTACT Software GmbH
# https://www.contact-software.com/
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

from os.path import normpath
from typing import TYPE_CHECKING

from path import Path

from csspin import die, tree

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
        self.type: list = []
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

    def coerce(
        self: PathDescriptor, value: str | Callable | None
    ) -> str | Path | Callable | None:
        if value not in (None, "") and not callable(value):
            return Path(normpath(value))  # type: ignore[type-var]
        return value


@descriptor("str")
class StringDescriptor(BaseDescriptor):
    """Descriptor for handling string values."""

    def coerce(self: StringDescriptor, value: str | Callable) -> str | Callable:
        return str(value) if not callable(value) else value


@descriptor("secret")
class SecretDescriptor(BaseDescriptor):
    """Descriptor for handling string values."""

    def coerce(self: SecretDescriptor, value: str | Callable) -> str | Callable:
        return str(value) if not callable(value) else value


@descriptor("int")
class IntDescriptor(BaseDescriptor):
    """Descriptor for handling integer values."""

    def coerce(self: IntDescriptor, value: int | Callable) -> int | Callable:
        return int(value) if not callable(value) else value


@descriptor("float")
class FloatDescriptor(BaseDescriptor):
    """Descriptor for handling float values."""

    def coerce(self: FloatDescriptor, value: float | Callable) -> float | Callable:
        return float(value) if not callable(value) else value


@descriptor("bool")
class BoolDescriptor(BaseDescriptor):
    """Descriptor for handling boolean values."""

    def coerce(self: BoolDescriptor, value: bool | str | Callable) -> bool | Callable:
        return bool(value) if not callable(value) else value

    def get_default(self: BoolDescriptor) -> bool:  # pylint: disable=arguments-differ
        return super().get_default(False)  # type: ignore[no-any-return]


@descriptor("list")
class ListDescriptor(BaseDescriptor):
    """
    Descriptor for handling lists, splitting string values and coercing them to
    lists.
    """

    def coerce(self: ListDescriptor, value: Iterable | Callable) -> list | Callable:
        if isinstance(value, str):
            return list(value.split())
        if callable(value):
            return value
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
        die(f"Unknown type '{description['type'][0]}' found in schema configuration.")
    return factory(description)  # type: ignore[return-value,misc]


def schema_load(fn: str) -> Type[BaseDescriptor]:
    props = tree.tree_load(fn)
    return build_schema(props)


def build_schema(props: tree.ConfigTree) -> Type[BaseDescriptor]:
    desc = {"type": "object", "properties": props}
    return build_descriptor(desc)
