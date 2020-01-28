# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys
import click
import shutil
import subprocess
import collections
import pickle
from contextlib import contextmanager

import yaml


def echo(*msg, **kwargs):
    if not CONFIG.quiet:
        msg = interpolate(msg)
        click.echo(click.style("spin: ", fg="green"), nl=False)
        click.echo(" ".join(msg), **kwargs)


def cd(where):
    echo("cd", where)
    os.chdir(where)


def exists(path):
    (path,) = interpolate((path,))
    return os.path.exists(path)


def mkdir(what):
    echo("mkdir", what)
    os.mkdir(what)


def rmtree(d):
    (d,) = interpolate((d,))
    echo("rmtree", d)
    shutil.rmtree(d)


def die(*msg, **kwargs):
    raise click.ClickException(" ".join(msg))


def sh(*cmd, **kwargs):
    cmd = interpolate(cmd)
    if not kwargs.pop("silent", False):
        echo(click.style(" ".join(cmd), bold=True))
    shell = kwargs.pop("shell", len(cmd) == 1)
    return subprocess.run(cmd, shell=shell, **kwargs)


def _read_file(fn, mode):
    (fn,) = interpolate((fn,))
    with open(fn, mode) as f:
        return f.read()


def _write_file(fn, mode, data):
    (fn,) = interpolate((fn,))
    with open(fn, "wb") as f:
        f.write(data)


def readbytes(fn):
    return _read_file(fn, "rb")


def writebytes(fn, data):
    return _write_file(fn, "wb", data)


def readtext(fn):
    return _read_file(fn, "r")


def writetext(fn, data):
    return _write_file(fn, "w", data)


def persist(fn, data):
    writebytes(fn, pickle.dumps(data))


def unpersist(fn, default=None):
    try:
        return pickle.loads(readbytes(fn))
    except FileNotFoundError:
        return default


class Memoizer(object):
    def __init__(self, fn):
        self._fn = fn
        self._items = unpersist(fn, [])

    def check(self, item):
        return item in self._items

    def add(self, item):
        self._items.append(item)

    def finalize(self):
        persist(self._fn, self._items)


@contextmanager
def memoizer(fn):
    m = Memoizer(fn)
    yield m
    m.finalize()


NSSTACK = []


@contextmanager
def namespaces(*nslist):
    for ns in nslist:
        NSSTACK.append(ns)
    yield
    for ns in nslist:
        NSSTACK.pop()


def interpolate(literals, *extra_dicts):
    out = []
    caller_frame = sys._getframe(2)
    caller_globals = caller_frame.f_globals
    caller_locals = collections.ChainMap(
        caller_frame.f_locals, CONFIG, os.environ, *extra_dicts, *NSSTACK,
    )
    for literal in literals:
        while True:
            previous = literal
            literal = eval(
                "f'''%s'''" % literal, caller_globals, caller_locals
            )
            if previous == literal:
                break
        out.append(literal)
    return out


class ConfigLoader(yaml.Loader):
    pass


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return Config(loader.construct_pairs(node))


ConfigLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
)


class Config(dict):
    def __getattr__(self, name, default=None):
        if name not in self:
            raise AttributeError(f"config key {name} not found")
        return self.get(name, default)

    def __setattr__(self, name, value):
        self[name] = value


def merge_config(target, source):
    for key, value in source.items():
        if key not in target:
            target[key] = value
        elif isinstance(value, dict):
            merge_config(target[key], value)


def config(**kwargs):
    return Config(kwargs)


def load_config(fname):
    with open(fname) as f:
        return yaml.load(f, ConfigLoader)


# This is the global configuration tree.
CONFIG = config()


def get_tree():
    return CONFIG


def set_tree(cfg):
    global CONFIG
    CONFIG = cfg
    return cfg
