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


class ConfigTree(OrderedDict):
    """A specialization of `OrderedDict` that we use to store the
    configuration tree internally.

    `ConfigTree` has three features over `OrderedDict`: first, it
    behaves like a "bunch", i.e. items can be access as dot
    expressions (``config.myprop``). Second, each subtree is linked to
    its parent, to enable the computation of full names:

    >>> tree_keyname(parent.subtree, "prop")
    'parent.subtree.prop'

    Third, we keep track of the locations settings came from. This is
    done automatically, i.e for each update operation we inspect the
    callstack and store source file name and line number. For data
    read from another source (e.g. a YAML file), the location
    information can be update manually via `tree_set_keyinfo`.

    Note that APIs used to access tracking information are *not* part
    of this class, as each identifier we add may clash with property
    names used.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__keyinfo = {}
        self.__parentinfo = None
        for key, value in self.items():
            self.__keyinfo[key] = _call_location(2)
            if isinstance(value, ConfigTree):
                value.__parentinfo = ParentInfo(self, key)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        _set_callsite(self, key, 3, value)

    def setdefault(self, key, default=None):
        val = super().setdefault(key, default)
        _set_callsite(self, key, 3, default)
        return val

    # __setattr__ and __getattr__ give the configuration tree "bunch"
    # behaviour, i.e. one can access the dictionary items as if they
    # were properties; this makes for a more convenient notation when
    # using the settings in code and f-like interpolation expressions.

    def __setattr__(self, name, value):
        if name.startswith("_ConfigTree__"):
            # "private" variables must not go into the dictionary,
            # obviously.
            object.__setattr__(self, name, value)
        else:
            self[name] = value
            _set_callsite(self, name, 3, value)

    def __getattr__(self, name):
        if name in self:
            return self.get(name)
        raise AttributeError(f"No property '{name}'")


def tree_update_key(config, key, value):
    OrderedDict.__setitem__(config, key, value)


def _call_location(depth):
    fn, lno, _, _, _ = inspect.getframeinfo(sys._getframe(depth))
    return KeyInfo(fn, lno)


def _set_callsite(self, key, depth, value):
    if hasattr(self, "_ConfigTree__keyinfo"):
        self._ConfigTree__keyinfo[key] = _call_location(depth)
    tree_set_parent(value, self, key)


def tree_set_keyinfo(self, key, ki):
    if hasattr(self, "_ConfigTree__keyinfo"):
        self._ConfigTree__keyinfo[key] = ki


def tree_keyinfo(self, k):
    return self._ConfigTree__keyinfo[k]


def tree_set_parent(self, parent, name):
    if hasattr(self, "_ConfigTree__parentinfo"):
        self._ConfigTree__parentinfo = ParentInfo(parent, name)


def tree_keyname(self, key):
    path = [key]
    try:
        parentinfo = self._ConfigTree__parentinfo
        while parentinfo:
            path.insert(0, parentinfo.key)
            parentinfo = parentinfo.parent._ConfigTree__parentinfo
    except AttributeError:
        pass
    return ".".join(path)


def tree_build(data, fn):
    config = ConfigTree(data)
    for key, value in data.items():
        if isinstance(value, dict):
            config[key] = tree_build(value, fn)
            tree_set_parent(config[key], config, key)
        ki = KeyInfo(fn, data.lc.key(key)[0] + 1)
        tree_set_keyinfo(config, key, ki)
    return config


def tree_load(fn):
    yaml = ruamel.yaml.YAML()
    with open(fn) as f:
        data = yaml.load(f)
    return tree_build(data, fn)


def tree_walk(config, indent=""):
    """Walk configuration tree depth-first, yielding the key, its value,
    the full name of the key, the tracking information and an
    indentation string that increases by ``" "`` for each level.
    """
    for key, value in config.items():
        yield key, value, tree_keyname(config, key), tree_keyinfo(
            config, key
        ), indent
        if isinstance(value, ConfigTree):
            for key, value, fullname, info, subindent in tree_walk(
                value, indent + "  "
            ):
                yield key, value, fullname, info, subindent


def tree_dump(tree):
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
        for _, _, _, info, _ in tree_walk(tree)
    )
    separator = "|"
    for key, value, _fullname, info, indent in tree_walk(tree):
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
