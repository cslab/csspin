# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""This is the fabulous scripting API, concise and powerful."""

import os
import click
import shutil
import subprocess
import collections
import pickle
from contextlib import contextmanager

import yaml


def echo(*msg, **kwargs):
    """Say something."""
    if not CONFIG.quiet:
        msg = interpolate(msg)
        click.echo(click.style("spin: ", fg="green"), nl=False)
        click.echo(" ".join(msg), **kwargs)


class DirectoryChanger(object):
    def __init__(self, path):
        path = interpolate1(path)
        self._cwd = os.getcwd()
        echo("cd", path)
        os.chdir(path)

    def __enter__(self):
        pass

    def __exit__(self, *args):
        os.chdir(self._cwd)


def cd(path):
    """Change directory. The `path` argument is interpolated against the
    configuration tree.

    `cd` can be used either as a function or as a context
    manager. When uses as a context manager, the working directory is
    changed back to what it was before the ``with`` block.

    You can do this:

    >>> cd("{spin.project_root}")

    ... or that:

    >>> with cd("{spin.project_root}"):
    ...    <do something in this directory>

    """
    return DirectoryChanger(path)


def exists(path):
    """Check wether `path` exists. The argument is interpolated against
    the configuration tree."""
    path = interpolate1(path)
    return os.path.exists(path)


def mkdir(path):
    """Ensure that `path` exists.

    If necessary, directories are recursively created to make `path`
    available. The argument is interpolated against the configuration
    tree.
    """
    path = interpolate1(path)
    if not exists(path):
        echo("mkdir", path)
        os.makedirs(path)
    return path


def rmtree(path):
    """Recursively remove `path` and everything it contains. The argument
    is interpolated agains the configuration tree.

    Obviously, this should be used with care.

    """
    path = interpolate1(path)
    echo("rmtree", path)
    shutil.rmtree(path)


class SpinError(click.ClickException):
    pass


def die(*msg, **kwargs):
    """Print error message to stderr and terminate ``spin`` with an error
    return code."""
    raise SpinError(" ".join(msg))


class Command(object):
    """Create a function that is a shrink-wrapped shell command.

    The callable returned behaves like :py:func:`sh`, accepting
    additional arguments for the wrapper command as positional
    parameters. All positional arguments are interpolated against the
    configuration tree.

    Example:

    >>> install = Command("pip", "install")
    >>> install("spin")

    FIXME: document ``quiet`` or remove it!

    """

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
    """Run a command. All positional arguments are interpolated against
    the configuration tree.

    >>> sh("ls", "{HOME}")

    """
    cmd = interpolate(cmd)
    if not kwargs.pop("silent", False):
        echo(click.style(" ".join(cmd), bold=True))
    shell = kwargs.pop("shell", len(cmd) == 1)
    cpi = subprocess.run(cmd, shell=shell, **kwargs)
    if cpi.returncode:
        die(f"Command failed with return code {cpi.returncode}")
    return cpi


def setenv(**kwargs):
    """Set or unset one or more environment variables. The values of
    keyword arguments are interpolated against the configuration tree.

    Passing ``None`` as a value removes the environment variable.

    >>> setenv(FOO="{spin.foo}", BAR="{bar.options}")

    """
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
    """Maintain a persistent base of simple facts.

    Facts are loaded from file `fn`. The argument is interpolated
    against the configuration tree. If `fn` does not exist, there are
    no facts.
    """

    def __init__(self, fn):
        self._fn = fn
        self._items = unpersist(fn, [])

    def check(self, item):
        """Check wether `item` is a know fact."""
        return item in self._items

    def add(self, item):
        """Add `item` to the fact base."""
        self._items.append(item)

    def save(self):
        """Save the updated fact base."""
        persist(self._fn, self._items)


@contextmanager
def memoizer(fn):
    """Context manager for creating a :py:class:`Memoizer` that
    automatically saves the fact base.

    >>> with memoizer("facts.memo") as m:
    ...   m.add("fact1")
    ...   m.add("fact2")

    """
    m = Memoizer(fn)
    yield m
    m.save()


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
        # Interpolate until we reach a fixpoint -- this allows for
        # nested variables.
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


class _ConfigLoader(yaml.Loader):
    pass


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return Config(loader.construct_pairs(node))


_ConfigLoader.add_constructor(
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
    """Create a configuration tree, setting the keywords to the given
    values.

    Nested trees are build by using `config()` for values:

    >>> config(subtree=config(key1="...", key2="..."))
    """
    return Config(kwargs)


def load_config(fname):
    with open(fname) as f:
        return yaml.load(f, _ConfigLoader)


# This is the global configuration tree.
CONFIG = config()


def get_tree():
    return CONFIG


def set_tree(cfg):
    global CONFIG
    CONFIG = cfg
    return cfg
