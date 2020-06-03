# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from path import Path

from . import tree


class SchemaError(TypeError):
    pass


class BaseDescriptor:
    def __init__(self, description):
        self._keyinfo = None
        for key, value in description.items():
            setattr(self, key, value)
            if key == "default":
                self._keyinfo = tree.tree_keyinfo(description, key)

    def coerce(self, value):
        return value

    def get_default(self, defaultdefault=None):
        return getattr(self, "default", defaultdefault)


DESCRIPTOR_REGISTRY = {}


def descriptor(tag):
    def decorator(cls):
        DESCRIPTOR_REGISTRY[tag] = cls

    return decorator


@descriptor("path")
class PathDescriptor(BaseDescriptor):
    def coerce(self, value):
        if value is not None:
            return Path(value)
        return value


@descriptor("str")
class StringDescriptor(BaseDescriptor):
    def coerce(self, value):
        return str(value)


@descriptor("boolean")
class BoolDescriptor(BaseDescriptor):
    def coerce(self, value):
        return bool(value)

    def get_default(self):
        return super().get_default(False)


@descriptor("list")
class ListDescriptor(BaseDescriptor):
    def coerce(self, value):
        if isinstance(value, str):
            value = value.split()
        return list(value)

    def get_default(self):
        return super().get_default([])


@descriptor("object")
class ObjectDescriptor(BaseDescriptor):
    def __init__(self, description):
        super().__init__(description)
        if not hasattr(self, "properties"):
            self.properties = tree.ConfigTree()
        for key, value in self.properties.items():
            ki = tree.tree_keyinfo(self.properties, key)
            odesc = build_descriptor(value)
            self.properties[key] = odesc
            if odesc._keyinfo is None:
                odesc._keyinfo = ki

    def get_default(self):
        data = super().get_default(tree.ConfigTree())
        for key, desc in self.properties.items():
            data[key] = desc.get_default()
            if desc._keyinfo:
                tree.tree_set_keyinfo(data, key, desc._keyinfo)
        data._ConfigTree__schema = self
        return data

    def coerce(self, value):
        if not isinstance(value, dict):
            raise SchemaError("dictionary required")
        return value


def build_descriptor(description):
    description["type"] = description.get("type", "object").split()
    factory = DESCRIPTOR_REGISTRY.get(description["type"][0])
    if factory is None:
        print(f"No factory for {description['type']}")
    return factory(description)


def schema_load(fn):
    props = tree.tree_load(fn)
    return build_schema(props)


def build_schema(props):
    desc = {"type": "object", "properties": props}
    schema = build_descriptor(desc)
    return schema
