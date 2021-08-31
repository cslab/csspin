# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""This is the core API of spin."""

import collections
import inspect
import logging
import os
import pickle
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager

import click


def echo(*msg, **kwargs):
    """Say something."""
    if not CONFIG.quiet:
        msg = interpolate(msg)
        click.echo(click.style("spin: ", fg="green"), nl=False)
        click.echo(" ".join(msg), **kwargs)


class DirectoryChanger:
    """A simple class to change the current directory.

    Change directory on construction, and restore the cwd when used as
    a context manager.
    """

    def __init__(self, path):
        """Change directory."""
        path = interpolate1(path)
        self._cwd = os.getcwd()
        echo("cd", path)
        os.chdir(path)

    def __enter__(self):
        """Nop."""

    def __exit__(self, *args):
        """Change back to where we came from."""
        os.chdir(self._cwd)


def cd(path):
    """Change directory.

    The `path` argument is interpolated against the configuration
    tree.

    `cd` can be used either as a function or as a context
    manager. When used as a context manager, the working directory is
    changed back to what it was before the ``with`` block.

    You can do this:

    >>> cd("{spin.project_root}")

    ... or that:

    >>> with cd("{spin.project_root}"):
    ...    <do something in this directory>

    """
    return DirectoryChanger(path)


def exists(path):
    """Check whether `path` exists. The argument is interpolated against
    the configuration tree.

    """
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
    is interpolated against the configuration tree.

    Obviously, this should be used with care.

    """
    path = interpolate1(path)
    echo("rmtree", path)
    shutil.rmtree(path)


class SpinError(click.ClickException):
    pass


def die(*msg):
    """Print error message to stderr and terminate ``spin`` with an error
    return code."""
    raise SpinError(" ".join(msg))


class Command:
    """Create a function that is a shrink-wrapped shell command.

    The callable returned behaves like :py:func:`sh`, accepting
    additional arguments for the wrapper command as positional
    parameters. All positional arguments are interpolated against the
    configuration tree.

    Example:

    >>> install = Command("pip", "install")
    >>> install("spin")

    """

    def __init__(self, *cmd):
        self._cmd = list(cmd)

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
    shell = kwargs.pop("shell", len(cmd) == 1)
    silent = kwargs.get("silent", False)

    if sys.platform == "win32":
        shell = True
        if len(cmd) == 1:
            cmd = shlex.split(cmd[0].replace("\\", "\\\\"))

    if not kwargs.pop("silent", False):
        echo(click.style(" ".join(cmd), bold=True))

    try:
        t0 = time.monotonic()
        cpi = subprocess.run(cmd, shell=shell, check=True, **kwargs)
        t1 = time.monotonic()
        if not silent and get_tree().verbose:
            echo(click.style("[%g seconds]" % (t1 - t0), fg="green"))
    except FileNotFoundError as ex:
        die(str(ex))
    except subprocess.CalledProcessError as ex:
        cmd = cmd if isinstance(cmd, str) else subprocess.list2cmdline(cmd)
        die(f"Command '{cmd}' failed with return code {ex.returncode}")

    return cpi


EXPORTS = {}


def setenv(*args, **kwargs):
    """Set or unset one or more environment variables. The values of
    keyword arguments are interpolated against the configuration tree.

    Passing ``None`` as a value removes the environment variable.

    >>> setenv(FOO="{spin.foo}", BAR="{bar.options}")

    """
    for key, value in kwargs.items():
        if value is None:
            if not args:
                echo(click.style(f"unset {key}", bold=True))
            os.environ.pop(key, None)
            EXPORTS[key] = None
        else:
            value = interpolate1(value)
            if get_tree().verbose:
                if not args:
                    echo(click.style(f"set {key}={value}", bold=True))
                else:
                    echo(click.style(args[0], bold=True))
            os.environ[key] = value
            EXPORTS[key] = value


def _read_file(fn, mode):
    fn = interpolate1(fn)
    with open(fn, mode) as f:
        return f.read()


def _write_file(fn, mode, data):
    fn = interpolate1(fn)
    with open(fn, mode) as f:
        f.write(data)


def readbytes(fn):
    return _read_file(fn, "rb")


def writebytes(fn, data):
    return _write_file(fn, "wb", data)


def readtext(fn):
    return _read_file(fn, "r")


def writetext(fn, data):
    return _write_file(fn, "w", data)


def appendtext(fn, data):
    return _write_file(fn, "a", data)


def persist(fn, data):
    writebytes(fn, pickle.dumps(data))


def unpersist(fn, default=None):
    try:
        return pickle.loads(readbytes(fn))
    except FileNotFoundError:
        return default


class Memoizer:
    """Maintain a persistent base of simple facts.

    Facts are loaded from file `fn`. The argument is interpolated
    against the configuration tree. If `fn` does not exist, there are
    no facts.
    """

    def __init__(self, fn):
        self._fn = fn
        self._items = unpersist(fn, [])

    def check(self, item):
        """Check whether `item` is a know fact."""
        return item in self._items

    def clear(self):
        """Remove all items"""
        self._items = []

    def items(self):
        return self._items

    def add(self, item):
        """Add `item` to the fact base."""
        self._items.append(item)
        self.save()

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
    for _ in nslist:
        NSSTACK.pop()


def interpolate1(literal, *extra_dicts):
    where_to_look = collections.ChainMap(
        {"config": CONFIG}, CONFIG, os.environ, *extra_dicts, *NSSTACK
    )
    while True:
        # Interpolate until we reach a fixpoint -- this allows for
        # nested variables.
        previous = literal
        literal = eval("rf'''%s'''" % literal, {}, where_to_look)  # noqa
        if previous == literal:
            break
    return literal


def interpolate(literals, *extra_dicts):
    out = []
    for literal in literals:
        out.append(interpolate1(literal, *extra_dicts))
    return out


def config(*args, **kwargs):
    from .tree import ConfigTree

    return ConfigTree(*args, **kwargs, __ofs_frames__=1)


def readyaml(fname):
    from .tree import tree_load

    fname = interpolate1(fname)
    return tree_load(fname)


def download(url, location):
    url, location = interpolate((url, location))
    echo(f"Download {url} -> {location} ...")
    response = urllib.request.urlopen(url)
    data = response.read()
    writebytes(location, data)


# This is the global configuration tree.
CONFIG = config()


def get_tree():
    return CONFIG


def set_tree(cfg):
    global CONFIG
    CONFIG = cfg
    return cfg


def argument(**kwargs):
    def wrapper(param_name):
        return click.argument(param_name, **kwargs)

    return wrapper


def option(*args, **kwargs):
    def wrapper(param_name):
        return click.option(*args, **kwargs)

    return wrapper


def task(*args, **kwargs):
    from . import cli

    def task_wrapper(fn, group=cli.commands):
        def alternate_callback(*args, **kwargs):
            return fn(get_tree(), *args, **kwargs)

        task_object = fn
        context_settings = config()
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())
        if param_names:
            if param_names[0] == "ctx":
                task_object = click.pass_context(fn)
                param_names.pop(0)
        pass_config = False
        for pn in param_names:
            if pn == "cfg":
                pass_config = True
                continue
            if pn == "args":
                context_settings.ignore_unknown_options = True
                context_settings.allow_extra_args = True
                task_object = click.argument("args", nargs=-1)(task_object)
                continue
            param = sig.parameters[pn]
            task_object = param.annotation(pn)(task_object)
        hook = kwargs.pop("when", None)
        aliases = kwargs.pop("aliases", [])
        group = kwargs.pop("group", group)
        task_object = group.command(*args, **kwargs, context_settings=context_settings)(
            task_object
        )
        if hook:
            cfg = get_tree()
            hook_tree = cfg.get("hooks", config())
            hooks = hook_tree.setdefault(hook, [])
            hooks.append(task_object)
        for alias in aliases:
            group.register_alias(alias, task_object)
        if pass_config:
            task_object.callback = alternate_callback
        return task_object

    return task_wrapper


def group(*args, **kwargs):
    from . import cli

    def group_decorator(fn):
        def subtask(*args, **kwargs):
            def task_decorator(fn):
                cmd = task(*args, **kwargs, group=grp)(fn)
                return cmd

            return task_decorator

        kwargs["cls"] = cli.GroupWithAliases
        grp = cli.commands.group(*args, **kwargs)(click.pass_context(fn))
        grp.task = subtask
        return grp

    return group_decorator


def invoke(hook, *args, **kwargs):
    ctx = click.get_current_context()
    cfg = get_tree()
    for task_object in cfg.hooks.setdefault(hook, []):
        ctx.invoke(task_object, *args, **kwargs)


def toporun(cfg, *fn_names, reverse=False):
    """Run plugin functions named in 'fn_names' in topological order."""
    plugins = cfg.topo_plugins
    if reverse:
        plugins = reversed(plugins)
    for func_name in fn_names:
        logging.info(f"toporun: {func_name}")
        for pi_name in plugins:
            pi_mod = cfg.loaded[pi_name]
            initf = getattr(pi_mod, func_name, None)
            if initf:
                logging.info(f"  {pi_name}.{func_name}()")
                initf(cfg)


def main(*args, **kwargs):
    from .cli import cli

    if not args:
        args = None
    kwargs["auto_envvar_prefix"] = "SPIN"
    kwargs.setdefault("standalone_mode", False)
    cli.click_main_kwargs = kwargs
    cli.main(args, **kwargs)


def _main(*args, **kwargs):
    return main(*args, standalone_mode=True, **kwargs)
