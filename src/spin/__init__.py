# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""This is the plugin API of spin. It contains functions and classes
that are necessary for plugins to register themselves with spin,
e.g. :py:func:`task`, and convenience APIs that aim to simplify plugin
implementation.

spin's task management (aka subcommands) is just a thin wrapper on top
of the venerable `package click
<https://click.palletsprojects.com/en/8.0.x/>`_, so to create any
slightly advanced command line interfaces for plugins you want to make
yourself comfortable with click's documentation.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Type

import packaging.version

if TYPE_CHECKING:
    from typing import Any, Callable, Generator
    from spin.tree import ConfigTree

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
from typing import Hashable

import click
import packaging
import xdg
from path import Path

__all__ = [
    "echo",
    "info",
    "warn",
    "error",
    "cd",
    "exists",
    "mkdir",
    "rmtree",
    "die",
    "Command",
    "sh",
    "backtick",
    "setenv",
    "readbytes",
    "writebytes",
    "readtext",
    "writetext",
    "appendtext",
    "persist",
    "unpersist",
    "memoizer",
    "namespaces",
    "interpolate1",
    "interpolate",
    "config",
    "readyaml",
    "download",
    "argument",
    "option",
    "task",
    "group",
    "invoke",
    "toporun",
    "Path",
    "Memoizer",
]


def echo(*msg: str, resolve: bool = False, **kwargs: Any) -> None:
    """Print a message to the console by joining the positional arguments
    `msg` with spaces.

    `echo` is meant for messages that explain to the user what spin is doing
    (e.g. *echoing* commands launched). It will remain silent though when ``spin``
    is run with the ``--quiet`` flag. If the parameter ``resolve`` is set to
    ``True``, the arguments are interpolated against the configuration tree.

    `echo` supports the same keyword arguments as Click's :py:func:`click.echo`.

    """
    if not CONFIG.quiet:
        if resolve:
            msg = interpolate(msg)
        click.echo(click.style("spin: ", fg="green"), nl=False)
        click.echo(click.style(" ".join(msg), bold=True), **kwargs)


def info(*msg: str, **kwargs: Any) -> None:
    """Print a message to the console by joining the positional arguments
    `msg` with spaces.

    Arguments are interpolated against the configuration tree. `info`
    will remain silent unless ``spin`` is run with the ``--verbose``
    flag. `info` is meant for messages that provide additional details.

    `info` supports the same keyword arguments as Click's
    :py:func:`click.echo`.

    """
    if CONFIG.verbose:
        msg = interpolate(msg)  # type: ignore[assignment]
        click.echo(click.style("spin: ", fg="green"), nl=False)
        click.echo(" ".join(msg), **kwargs)


def warn(*msg: str, **kwargs: Any) -> None:
    """Print a warning message to the console by joining the positional
    arguments `msg` with spaces.

    Arguments are interpolated against the configuration tree. The
    output is written to standard error.

    `warn` supports the same keyword arguments as Click's
    :py:func:`click.echo`.

    """
    msg = interpolate(msg)  # type: ignore[assignment]
    click.echo(click.style("spin: warning: ", fg="yellow"), nl=False, err=True)
    click.echo(" ".join(msg), err=True, **kwargs)


def error(*msg: str, **kwargs: Any) -> None:
    """Print an error message to the console by joining the positional
    arguments `msg` with spaces.

    Arguments are interpolated against the configuration tree. The
    output is written to standard error.

    `error` supports the same keyword arguments as Click's
    :py:func:`click.echo`.

    """
    msg = interpolate(msg)  # type: ignore[assignment]
    click.echo(click.style("spin: error: ", fg="red"), nl=False, err=True)
    click.echo(" ".join(msg), err=True, **kwargs)


class DirectoryChanger:
    """A simple class to change the current directory.

    Change directory on construction, and restore the cwd when used as
    a context manager.
    """

    def __init__(self: DirectoryChanger, path: str | Path) -> None:
        """Change directory."""
        path = interpolate1(path)  # type: ignore[assignment]
        self._cwd = os.getcwd()
        echo("cd", path)
        os.chdir(path)

    def __enter__(self: DirectoryChanger) -> None:
        """Nop."""

    def __exit__(self: DirectoryChanger, *args: Any) -> None:
        """Change back to where we came from."""
        os.chdir(self._cwd)


def cd(path: str | Path) -> DirectoryChanger:
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


def exists(path: str | Path) -> bool:
    """Check whether `path` exists. The argument is interpolated against
    the configuration tree.

    """
    path = interpolate1(path)  # type: ignore[assignment]
    return os.path.exists(path)


def normpath(*args: str | Path) -> str:
    return os.path.normpath(os.path.join(*interpolate(args)))  # type: ignore[no-any-return]


def abspath(*args: str | Path) -> str:
    return os.path.abspath(normpath(*args))


def mkdir(path: str) -> str:
    """Ensure that `path` exists.

    If necessary, directories are recursively created to make `path`
    available. The argument is interpolated against the configuration
    tree.

    """
    path = interpolate1(path)  # type: ignore[assignment]
    if not exists(path):
        echo("mkdir", path)
        os.makedirs(path)
    return path


def rmtree(path: str) -> None:
    """Recursively remove `path` and everything it contains. The argument
    is interpolated against the configuration tree.

    Obviously, this should be used with care.

    """
    path = interpolate1(path)  # type: ignore[assignment]
    echo("rmtree", path)
    shutil.rmtree(path)


def die(*msg: Any) -> None:
    """Terminates ``spin`` with a non-zero return code and print the error
    message `msg`.

    Arguments are interpolated against the configuration tree.

    """
    msg = interpolate(msg)  # type: ignore[assignment]
    error(*msg)
    raise click.Abort(msg)


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

    def __init__(self: Command, *cmd: str) -> None:
        self._cmd = list(cmd)

    def append(self: Command, item: str) -> None:
        self._cmd.append(item)

    def __call__(
        self: Command, *args: str, **kwargs: Any
    ) -> subprocess.CompletedProcess | None:
        cmd = self._cmd + list(args)
        return sh(*cmd, **kwargs)


def sh(*cmd: str, **kwargs: Any) -> subprocess.CompletedProcess | None:
    """Run a program by building a command line from `cmd`.

    When multiple positional arguments are given, each is treated as
    one element of the command. When just one positional argument is
    used, `sh` assumes it to be a single command and splits it into
    multiple arguments using :py:func:`shlex.split`. The `cmd`
    arguments are interpolated against the configuration tree. When
    `silent` is ``False``, the resulting command line will be
    echoed. When `shell` is ``True``, the command line is passed to
    the system's shell. When `may_fail` is ``True``, sh tolerates
    failures when invocating the command.

    Other keyword arguments are passed into
    :py:func:`subprocess.run`.

    All positional arguments are interpolated against the
    configuration tree.

    >>> sh("ls", "{HOME}")

    """
    cmd = interpolate(cmd)  # type: ignore[assignment]
    shell = kwargs.pop("shell", len(cmd) == 1)
    check = kwargs.pop("check", True)
    may_fail = kwargs.pop("may_fail", False)
    env = argenv = kwargs.pop("env", None)
    if env:
        process_env = dict(os.environ)
        process_env.update(env)
        env = process_env

    executable = None
    if sys.platform == "win32":
        if len(cmd) == 1:
            cmd = shlex.split(cmd[0].replace("\\", "\\\\"))
        if not shell:
            executable = shutil.which(cmd[0])

    if not kwargs.pop("silent", False):

        def quote(arg: str) -> str:
            if len(cmd) > 1 and " " in arg:
                return f"'{arg}'"
            return arg

        echo(" ".join(quote(c) for c in cmd))

    cpi = None
    try:
        t0 = time.monotonic()
        logging.debug(
            "subprocess.run(%s, shell=%s, check=%s, env=%s, executable=%s, kwargs=%s",
            cmd,
            shell,
            check,
            argenv,
            executable,
            kwargs,
        )
        cpi = subprocess.run(
            cmd, shell=shell, check=check, env=env, executable=executable, **kwargs
        )
        t1 = time.monotonic()
        info(click.style(f"[{t1 - t0} seconds]", fg="cyan"))
    except FileNotFoundError as ex:
        msg = str(ex)
        if not may_fail:
            die(msg)
        warn(msg)
    except subprocess.CalledProcessError as ex:
        cmd = cmd if isinstance(cmd, str) else subprocess.list2cmdline(cmd)  # type: ignore[assignment,unreachable] # noqa: E501
        msg = f"Command '{cmd}' failed with return code {ex.returncode}"
        if not may_fail:
            die(msg)
        warn(msg)

    return cpi


def backtick(*cmd: str, **kwargs: Any) -> str:
    kwargs["stdout"] = subprocess.PIPE
    cpi = sh(*cmd, **kwargs)
    return cpi.stdout.decode()  # type: ignore[no-any-return,union-attr]


EXPORTS: dict = {}


def setenv(*args, **kwargs) -> None:
    """Set or unset one or more environment variables. The values of
    keyword arguments are interpolated against the configuration tree.

    Passing ``None`` as a value removes the environment variable.

    >>> setenv(FOO="{spin.foo}", BAR="{bar.options}")

    """
    for key, value in kwargs.items():
        if value is None:
            if not args:
                echo(f"unset {key}")
            os.environ.pop(key, None)
            EXPORTS[key] = None
        else:
            value = interpolate1(value)
            if not args:
                echo(f"set {key}={value}")
            else:
                echo(args[0])
            os.environ[key] = value
            EXPORTS[key] = value


def _read_file(fn: str | Path, mode: str) -> str | bytes:
    fn = interpolate1(fn)  # type: ignore[assignment]
    with open(fn, mode, encoding="utf-8" if "b" not in mode else None) as f:
        return f.read()  # type: ignore[no-any-return]


def readlines(fn: str | Path) -> list[str]:
    fn = interpolate1(fn)  # type: ignore[assignment]
    with open(fn, "r", encoding="utf-8") as f:
        return f.readlines()


def writelines(fn: str | Path, lines: str) -> None:
    fn = interpolate1(fn)  # type: ignore[assignment]
    with open(fn, "w", encoding="utf-8") as f:
        return f.writelines(lines)


def _write_file(fn: str | Path, mode: str, data: bytes | str) -> int:
    fn = interpolate1(fn)  # type: ignore[assignment]
    with open(fn, mode, encoding="utf-8" if "b" not in mode else None) as f:
        return f.write(data)


def readbytes(fn: str | Path) -> bytes:
    """`readbytes` reads binary data. The file name argument is
    interpolated against the configuration tree.

    """
    return _read_file(fn, "rb")  # type: ignore[return-value]


def writebytes(fn: str | Path, data: bytes) -> int:
    """Write `data`` to the file named `fn`.

    Data is binary data (`bytes`).  The file name argument is
    interpolated against the configuration tree.

    """
    return _write_file(fn, "wb", data)


def readtext(fn: str | Path) -> str:
    """Read an UTF8 encoded text from the file 'fn'.

    The file name argument is interpolated against the configuration
    tree.

    """
    return _read_file(fn, "r")  # type: ignore[return-value]


def writetext(fn: str | Path, data: str) -> int:
    """Write `data`, which is text (Unicode object of type `str`) to the
    file named `fn`.

    The file name argument is interpolated against the configuration tree.

    """
    return _write_file(fn, "w", data)


def appendtext(fn: str | Path, data: str) -> int:
    """Append `data`, which is text (Unicode object of type `str`) to the
    file named `fn`.

    The file name argument is interpolated against the configuration tree.

    """
    return _write_file(fn, "a", data)


def persist(fn: str | Path, data: Type[object]) -> int:
    """Persist the Python object(s) in `data` using :py:mod:`pickle`."""
    return writebytes(fn, pickle.dumps(data))


def unpersist(fn: str, default: Any | None = None) -> Any | None:
    """Load pickled Python object(s) from the file `fn`."""
    try:
        return pickle.loads(readbytes(fn))
    except FileNotFoundError:
        return default


class Memoizer:
    """Maintain a persistent base of simple facts.

    Facts are loaded from file `fn`. The argument is interpolated
    against the configuration tree. If `fn` does not exist, there are
    no facts.

    The `Memoizer` class stores and retrieves Python objects from the
    binary file named `fn`. The argument is interpolated against the
    configuration tree. `Memoizer` can be used to keep a simple
    "database". Spin internally uses Memoizers for e.g. keeping track
    of packages installed in a virtual environment.

    To ease the handling in `spin` scripts, there also is context
    manager called `memoizer` (note the lower case "m"). The context
    manager retrieves the database from the file and saves it back
    when the context is closed::

      >>> with memoizer(fn) as m:
      ...    if m.check("test"): ...

    There are *no* precautions for simultaneous access from multiple
    processes, writes will likely silently become lost.

    """

    def __init__(self: Memoizer, fn: str | Path) -> None:
        self._fn = fn
        self._items = unpersist(fn, [])

    def check(self: Memoizer, item: Iterable) -> bool:
        """Checks whether `item` is stored in the memoizer."""
        return item in self._items  # type: ignore[operator]

    def clear(self: Memoizer) -> None:
        """Remove all items"""
        self._items = []

    def items(self: Memoizer) -> Iterable:
        return self._items  # type: ignore[return-value]

    def add(self: Memoizer, item: Any) -> None:
        """Add `item` to the memoizer."""
        self._items.append(item)  # type: ignore[union-attr]
        self.save()

    def save(self: Memoizer) -> None:
        """Persist the current state of the memoizer.

        This is done automatically when using `memoizer` as a context
        manager.

        """
        persist(self._fn, self._items)  # type: ignore[arg-type]


@contextmanager
def memoizer(fn: str) -> Generator:
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
def namespaces(*nslist: str) -> Generator:
    """Add namespaces for interpolation."""
    for ns in nslist:
        NSSTACK.append(ns)
    yield
    for _ in nslist:
        NSSTACK.pop()


os.environ["SPIN_CONFIG"] = os.environ.get(
    "SPIN_CONFIG", Path(xdg.xdg_config_home()) / "spin"
)
os.environ["SPIN_CACHE"] = os.environ.get(
    "SPIN_CACHE", Path(xdg.xdg_cache_home()) / "spin"
)


def interpolate1(literal, *extra_dicts):
    """Interpolate a string or path against the configuration tree.

    If literal is not a string or path, it will be converted to a string prior
    interpolating.

    To avoid interpolation for literals or specific parts of a literal, curly
    braces can be used to escape curly braces, like regular f-string
    interpolation.

    Example:

    >>> interpolate1(
            '{{"header": {{"language": "en", "cache": "{SPIN_CACHE}"}}}}'
        )
    '{"header": {"language": "en", "cache": "/home/bts/.cache/spin"}}'

    """
    is_path = isinstance(literal, Path)
    if not is_path and not isinstance(literal, str):
        literal = str(literal)

    where_to_look = collections.ChainMap(
        {"config": CONFIG}, CONFIG, os.environ, *extra_dicts, *NSSTACK  # type: ignore[arg-type]
    )
    seen = set()

    while True:
        # Interpolate until we reach a fixpoint -- this allows for
        # nested variables.
        previous = literal
        seen.add(literal)

        # The whole literal.replace()-dance below is a *crude workaround* which
        # is necessary to support curly brackets escapes without dropping the
        # evaluation of nested variables. Doing this 'by the book' requires
        # substantially higher efforts which we're not ready to pay now. So we
        # take this shortcut consciously and will repay the TD later.
        #
        # *Note*: string reverting (below) is necessary to replace the outer
        # bracket pairs and not the inner.
        literal = literal[::-1].replace("}}", "<DOUBLE_BRACE_CLOSE>"[::-1])
        literal = literal[::-1].replace("{{", "<DOUBLE_BRACE_OPEN>")
        literal = eval(rf"rf''' {literal} '''", {}, where_to_look)[1:-1]  # noqa
        literal = literal.replace("<DOUBLE_BRACE_OPEN>", "{{")
        literal = literal.replace("<DOUBLE_BRACE_CLOSE>", "}}")
        if previous == literal:
            literal = literal.replace("{{", "{")
            literal = literal.replace("}}", "}")
            break
        if literal in seen:
            raise RecursionError(literal)
    if is_path:
        literal = Path(literal)
    return literal


def interpolate(literals: Iterable[Hashable], *extra_dicts: dict) -> list:
    """
    Interpolate an iterable of hashable items against the configuration tree.
    """
    out = []
    for literal in literals:
        # We allow None, which gets filtered out here, to enable
        # simple argument configuration, e.g. something like:
        # sh("...", "-q" if cfg.quiet else None, ...)
        if literal is not None:
            out.append(interpolate1(literal, *extra_dicts))
    return out


def config(*args: Any | None, **kwargs: dict) -> ConfigTree:
    """`config` creates a configuration subtree:

    >>> config(a="alpha", b="beta)
    {"a": "alpha", "b": "beta}

    Plugins use `config` to declare their ``defaults`` tree.

    """

    from spin.tree import ConfigTree

    return ConfigTree(*args, **kwargs, __ofs_frames__=1)


def readyaml(fname: str | Path) -> ConfigTree:
    """Read a YAML file."""
    from spin.tree import tree_load

    fname = interpolate1(fname)  # type: ignore[assignment]
    return tree_load(fname)


def download(url: str, location: str | Path) -> None:
    """Download data from `url` to `location`."""
    url, location = interpolate((url, location))
    dirname = os.path.dirname(location)
    mkdir(dirname)
    echo(f"Download {url} -> {location} ...")

    with urllib.request.urlopen(url) as response:
        data = response.read()
        writebytes(location, data)


# This is the global configuration tree.
CONFIG = config()


def get_tree() -> ConfigTree:
    """Return the global configuration tree."""
    return CONFIG


def set_tree(cfg: ConfigTree) -> ConfigTree:
    # Intentionally undocumented
    global CONFIG  # pylint: disable=global-statement
    CONFIG = cfg
    return cfg


def argument(**kwargs: Any) -> Callable:
    """Annotations task arguments.

    This works just like :py:func:`click.argument`, accepting all the
    same parameters. Example:

    .. code-block:: python
        :linenos:

        @task()
        def mytask(outfile: argument(type="...", help="...")):
            foo("do something")

    """

    def wrapper(param_name: str) -> Callable:
        return click.argument(param_name, **kwargs)

    return wrapper


def option(*args: Any, **kwargs: Any) -> Callable:
    """Annotations for task options.

    This works just like :py:func:`click.option`, accepting the same
    parameters. Example:

    .. code-block:: python
        :linenos:

        @task()
        def mytask(
            outfile: option(
                "-o",
                "outfile",
                default="-",
                type=click.File("w"),
                help="... usage information ...",
            )
        ):
            foo("do something")

    """

    def wrapper(param_name: str) -> Callable:
        return click.option(*args, **kwargs)

    return wrapper


def task(*args: Any, **kwargs: Any) -> Callable:
    """Decorator that creates a task. This is a wrapper around Click's
    :py:func:`click.command` decorator, with some extras:

    * a string keyword argument ``when`` adds the task to the list of
      commands to run using :py:func:`invoke`

    * `aliases` is a list of aliases for the command (e.g. "check" is
      an alias for "lint")

    * ``noenv=True`` registers the command as a global command, that
      can run without a provisioned environment

    `task` introspects the signature of the decorated function and
    handles certain argument names automatically:

    * ``ctx`` will pass the :py:class:`Click context object
      <click.Context>` into the task; this is rarely useful for spin
      tasks

    * ``cfg`` will automatically pass the configuration tree; this is
      very useful most of the time, except for the simplest of tasks

    * ``args`` will simply pass through all command line arguments
      by using the ``ignore_unknown_options`` and
      ``allow_extra_args`` options of the Click context; this is
      often used for tasks that launch a specific command line tool
      to enable arbitrary arguments


    All other arguments to the task must be annotated with either
    :py:func:`option` or :py:func:`argument`. They both support the
    same arguments as the corresponding decorators
    :py:func:`click.option` and :py:func:`click.argument`.

    A simple example:

    .. code-block:: python
        :linenos:

        @task()
        def simple_task(cfg, args):
            foo("do something")

    This would make ``simple_task`` available as a new subcommand of
    spin.

    More elaborate examples can be found in the built-in plugins
    shipping with spin.

    """

    # Import cli here, to avoid an import cycle
    from spin import cli  # pylint: disable=cyclic-import

    def task_wrapper(fn: Callable, group=cli.commands) -> Callable:
        task_object = fn
        pass_context = False
        context_settings = config()
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())
        if param_names and param_names[0] == "ctx":
            pass_context = True
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
        noenv = kwargs.pop("noenv", False)
        group = kwargs.pop("group", group)
        task_object = group.command(*args, **kwargs, context_settings=context_settings)(
            task_object
        )
        if noenv:
            cli.register_noenv(task_object.name)
        if group != cli.commands:  # pylint: disable=comparison-with-callable
            task_object.full_name = " ".join((group.name, task_object.name))
        else:
            task_object.full_name = task_object.name
        if hook:
            cfg = get_tree()
            hook_tree = cfg.get("hooks", config())
            hooks = hook_tree.setdefault(hook, [])
            hooks.append(task_object)
        for alias in aliases:
            group.register_alias(alias, task_object)

        def regular_callback(*args, **kwargs):
            ensure(task_object)
            return fn(*args, **kwargs)

        def alternate_callback(*args, **kwargs):
            ensure(task_object)
            return fn(get_tree(), *args, **kwargs)

        if pass_config:
            task_object.callback = alternate_callback
        elif pass_context:
            task_object.callback = click.pass_context(regular_callback)
        else:
            task_object.callback = regular_callback
        task_object.__doc__ = fn.__doc__
        return task_object

    return task_wrapper


def group(*args: Any, **kwargs: Any) -> Callable:
    """Decorator for task groups, to create nested commands.

    This works like :py:class:`click.Group`, but additionally supports
    subcommand aliases, that can be set via the `aliases` keyword
    argument to :py:func:`task`. Example:

    .. code-block:: python

       @group()
       def foo():
           pass


       @foo.task()
       def bar():
           pass

    The above example creates a ``spin foo bar`` command.

    """
    from spin import cli

    def group_decorator(fn: str | Path) -> Callable:
        def subtask(*args: Any, **kwargs: Any) -> Callable:
            def task_decorator(fn: str | Path):
                cmd = task(*args, **kwargs, group=grp)(fn)
                return cmd

            return task_decorator

        noenv = kwargs.pop("noenv", False)
        kwargs["cls"] = cli.GroupWithAliases
        grp = cli.commands.group(*args, **kwargs)(click.pass_context(fn))
        if noenv:
            cli.register_noenv(grp.name)
        grp.task = subtask
        return grp

    return group_decorator


def getmtime(fn: str | Path) -> float:
    """Get the modification of file `fn`.

    `fn` is interpolated against the configuration tree.

    """
    return os.path.getmtime(interpolate1(fn))  # type: ignore[arg-type]


def is_up_to_date(target: str | Path, sources: Iterable[str, Path]) -> bool:
    """Check whether `target` exists and is newer than all of the
    `sources`.

    """
    if not exists(target):
        return False
    if not isinstance(sources, Iterable):
        raise TypeError("'sources' must be type 'Iterable'")
    target_mtime = getmtime(target)
    source_mtimes = [getmtime(src) for src in sources] + [0.0]
    return target_mtime >= max(source_mtimes)


def run_script(script: list, env: dict | None = None) -> None:
    """Run a list of shell commands."""
    if isinstance(script, str) or not isinstance(script, Iterable):
        script = [str(script)]
    for line in script:
        sh(line, shell=True, env=env)


def run_spin(script: list) -> None:
    """Run a list of spin commands."""
    from spin.cli import commands

    if isinstance(script, str) or not isinstance(script, Iterable):
        script = [str(script)]

    for line in script:
        line = shlex.split(line.replace("\\", "\\\\"))
        try:
            echo("spin", " ".join(line), resolve=True)
            commands(line)
        except SystemExit as exc:
            if exc.code:  # pylint: disable=using-constant-test
                raise


def get_sources(tree: ConfigTree) -> list:
    sources = tree.get("sources", [])
    if not isinstance(sources, list):
        sources = [sources]
    return sources  # type: ignore[no-any-return]


def build_target(cfg: ConfigTree, target: str, phony: bool = False) -> None:
    info(f"target '{target}'{' (phony)' if phony else ''}")
    build_rules = cfg.get("build-rules", config())
    target_def = build_rules.get(target, None)
    if target_def is None:
        if not exists(target) and not phony:
            die(
                f"Sorry, I don't know how to produce '{target}'. You may want to"
                " add a rule to your spinfile.yaml in the 'build-rules'"
                " section."
            )
        return
    sources = get_sources(target_def)
    # First, build preconditions
    if sources:
        for source in sources:
            build_target(cfg, source, False)
    if not phony:
        if not is_up_to_date(target, sources):
            info(f"build '{target}'")
            script = target_def.get("script", [])
            spinscript = target_def.get("spin", [])
            run_script(script)
            run_spin(spinscript)
        else:
            info(f"{target} is up to date")


def ensure(command: click.core.Command) -> None:
    # Check 'command_name' for dependencies declared under
    # "build-rules", and make sure to produce it. This is used
    # internally and intentionally undocumented.
    logging.debug("checking preconditions for %s", command)
    cfg = get_tree()
    build_target(cfg, f"task {command.full_name}", phony=True)


def invoke(hook: str, *args: Any, **kwargs: Any) -> None:
    '''``invoke()`` invokes the tasks that have the ``when`` hook
    `hook`. As an example, here is the implementation of **lint**:

    .. code-block:: python

       @task(aliases=["check"])
       def lint(allsource: option("--all", "allsource", is_flag=True)):
           """Run all linters defined in this project"""
           invoke("lint", allsource=allsource)

    Note that in this case, all linters are required to support the
    ``allsource`` argument, i.e. the way a task that uses `invoke` is
    invoking other tasks is part of the call interface contract for
    linters: *all* linter tasks *must* support the ``allsource``
    argument as part of their Python function signature (albeit not
    necessarily the same command line flag ``--all``).
    '''
    ctx = click.get_current_context()
    cfg = get_tree()
    for task_object in cfg.hooks.setdefault(hook, []):
        # Filter kwargs so that plugins don't need to provide
        # options, just for being able to get called by a workflow
        task_opts = [
            param.name
            for param in task_object.params
            if isinstance(param, click.Option)
        ]
        pass_opts = {k: v for k, v in kwargs.items() if k in task_opts}

        ctx.invoke(task_object, *args, **pass_opts)


def toporun(cfg, *fn_names, reverse=False) -> None:
    """Run plugin functions named in 'fn_names' in topological order."""
    plugins = cfg.topo_plugins
    if reverse:
        plugins = reversed(plugins)
    for func_name in fn_names:
        logging.debug(f"toporun: {func_name}")
        for pi_name in plugins:
            pi_mod = cfg.loaded[pi_name]
            initf = getattr(pi_mod, func_name, None)
            if initf:
                logging.debug(f"  {pi_name}.{func_name}()")
                initf(cfg)


def main(*args: Any, **kwargs: Any) -> None:
    from spin.cli import cli

    if not args:
        args = None
    kwargs["auto_envvar_prefix"] = "SPIN"
    kwargs["complete_var"] = "XOKSAPOKA"
    kwargs.setdefault("standalone_mode", False)
    cli.click_main_kwargs = kwargs
    cli.main(args, **kwargs)


def _main(*args: Any, **kwargs: Any) -> None:
    return main(*args, standalone_mode=True, **kwargs)


def parse_version(verstr: str) -> packaging.version.Version:
    """Parse a version string."""
    return packaging.version.parse(verstr)


def get_requires(tree: ConfigTree, keyname: str) -> ConfigTree | list:
    """Access the 'requires.<keyname>' property in a subtree. Return [] if
    not there.
    """
    requires = tree.get("requires", config())
    return requires.get(keyname, [])
