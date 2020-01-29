# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
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
    path = interpolate1(path)
    return os.path.exists(path)


def mkdir(path):
    path = interpolate1(path)
    if not exists(path):
        echo("mkdir", path)
        os.makedirs(path)
    return path


def rmtree(d):
    d = interpolate1(d)
    echo("rmtree", d)
    shutil.rmtree(d)


class SpinError(click.ClickException):
    pass


def die(*msg, **kwargs):
    raise SpinError(" ".join(msg))


class Command(object):
    def __init__(self, *cmd, quiet=None):
        self._cmd = list(cmd)
        cfg = get_tree()
        if quiet and cfg.quiet:
            self.append(quiet)

    def append(self, item):
        self._cmd.append(item)

    def __call__(self, *args, **kwargs):
        cmd = self._cmd + list(args)
        return sh(*cmd, **kwargs)


def sh(*cmd, **kwargs):
    cmd = interpolate(cmd)
    if not kwargs.pop("silent", False):
        echo(click.style(" ".join(cmd), bold=True))
    shell = kwargs.pop("shell", len(cmd) == 1)
    cpi = subprocess.run(cmd, shell=shell, **kwargs)
    if cpi.returncode:
        die(f"Command failed with return code {cpi.returncode}")
    return cpi


def setenv(**kwargs):
    for key, value in kwargs.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = interpolate1(value)


def _read_file(fn, mode):
    fn = interpolate1(fn)
    with open(fn, mode) as f:
        return f.read()


def _write_file(fn, mode, data):
    fn = interpolate1(fn)
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


def interpolate1(literal, *extra_dicts):
    where_to_look = collections.ChainMap(
        CONFIG, os.environ, *extra_dicts, *NSSTACK,
    )
    while True:
        previous = literal
        literal = eval("f'''%s'''" % literal, {}, where_to_look)
        if previous == literal:
            break
    return literal


def interpolate(literals, *extra_dicts):
    out = []
    for literal in literals:
        out.append(interpolate1(literal, *extra_dicts))
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
