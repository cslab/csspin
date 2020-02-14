# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import inspect
import os
import sys
from collections import OrderedDict, namedtuple

import ruamel.yaml


KeyInfo = namedtuple("KeyInfo", ["file", "line"])
ParentInfo = namedtuple("ParentInfo", ["parent", "key"])


class ConfigDict(OrderedDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__keyinfo = {}
        self.__parentinfo = None
        for key, value in self.items():
            self.__keyinfo[key] = _call_location(2)
            if isinstance(value, ConfigDict):
                value.__parentinfo = ParentInfo(self, key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        _set_callsite(self, key, 3, value)

    def setdefault(self, key, default=None):
        val = super().setdefault(key, default)
        _set_callsite(self, key, 3, default)
        return val

    def __setattr__(self, name, value):
        if name.startswith("_ConfigDict__"):
            object.__setattr__(self, name, value)
        else:
            self[name] = value
            _set_callsite(self, name, 3, value)

    def __getattr__(self, name):
        if name in self:
            return self.get(name)
        raise AttributeError(f"No property '{name}'")


def set_item_no_keyinfo(config, key, value):
    OrderedDict.__setitem__(config, key, value)


def _call_location(depth):
    fn, lno, _, _, _ = inspect.getframeinfo(sys._getframe(depth))
    return KeyInfo(fn, lno)


def _set_callsite(self, key, depth, value):
    if hasattr(self, "_ConfigDict__keyinfo"):
        self._ConfigDict__keyinfo[key] = _call_location(depth)
    set_parent(value, self, key)


def _set_keyinfo(self, key, ki):
    if hasattr(self, "_ConfigDict__keyinfo"):
        self._ConfigDict__keyinfo[key] = ki


def keyinfo(self, k):
    return self._ConfigDict__keyinfo[k]


def set_parent(self, parent, name):
    if hasattr(self, "_ConfigDict__parentinfo"):
        self._ConfigDict__parentinfo = ParentInfo(parent, name)


def keyname(self, key):
    path = [key]
    try:
        parentinfo = self._ConfigDict__parentinfo
        while parentinfo:
            path.insert(0, parentinfo.key)
            parentinfo = parentinfo.parent._ConfigDict__parentinfo
    except AttributeError:
        pass
    return ".".join(path)


def build_tree(data, fn):
    config = ConfigDict(data)
    for key, value in data.items():
        if isinstance(value, dict):
            config[key] = build_tree(value, fn)
            set_parent(config[key], config, key)
        ki = KeyInfo(fn, data.lc.key(key)[0] + 1)
        _set_keyinfo(config, key, ki)
    return config


def loadyaml(fn):
    yaml = ruamel.yaml.YAML()
    with open(fn) as f:
        data = yaml.load(f)
    return build_tree(data, fn)


def walk_tree(config, indent=""):
    for key, value in config.items():
        yield key, value, keyname(config, key), keyinfo(config, key), indent
        if isinstance(value, ConfigDict):
            for key, value, fullname, info, subindent in walk_tree(
                value, indent + "  "
            ):
                yield key, value, fullname, info, subindent


def dumptree(tree):
    text = []

    def write(line):
        text.append(line)

    cwd = os.getcwd()
    home = os.path.expanduser("~")

    def shorten_filename(fn):
        if fn.startswith(cwd):
            return fn[len(cwd) + 1:]
        if fn.startswith(home):
            return f"~{fn[len(home):]}"
        return fn

    tagcolumn = max(
        len(f"{shorten_filename(info.file)}:{info.line}:")
        for _, _, _, info, _ in walk_tree(tree)
    )
    separator = "|"
    for key, value, _fullname, info, indent in walk_tree(tree):
        tag = f"{shorten_filename(info.file)}:{info.line}:"
        space = (tagcolumn - len(tag) + 1) * " "
        if isinstance(value, list):
            write(f"{tag}{space}{separator}{indent}{key}:")
            blank_location = len(f"{tag}{space}") * " "
            for item in value:
                write(f"{blank_location}{separator}{indent}  - {repr(item)}")
        elif isinstance(value, dict):
            write(f"{tag}{space}{separator}{indent}{key}:")
        else:
            write(f"{tag}{space}{separator}{indent}{key}: {repr(value)}")
    return "\n".join(text)
