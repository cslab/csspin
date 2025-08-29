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

# pylint: disable=too-many-lines

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

from enum import IntEnum
from typing import TYPE_CHECKING, Iterable, Type

import packaging.version
import platformdirs.unix

if TYPE_CHECKING:
    from typing import Any, Callable, Generator
    from csspin.tree import ConfigTree
    from csspin.cli import GroupWithAliases

import collections
import inspect
import os
import pickle
import re
import shlex
import shutil
import subprocess
import sys
import urllib.request
from contextlib import contextmanager
from traceback import format_exc

import click
import packaging
import platformdirs
from path import Path

__all__ = [
    "debug",
    "echo",
    "info",
    "warn",
    "error",
    "cd",
    "copy",
    "confirm",
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
    "EXPORTS",
]

secrets: set[str] = set()


def obfuscate(msg: Iterable[str] | str) -> list[str] | str:
    mask = "*******"

    if isinstance(msg, str):
        new_msg = msg
        for secret in secrets:
            new_msg = new_msg.replace(secret, mask)
        return new_msg

    elif isinstance(msg, Iterable):
        msg_list: list[str] = []
        for string in msg:
            for secret in secrets:
                string = string.replace(secret, mask)
            msg_list.append(string)
        return msg_list


def echo(*msg: str, resolve: bool = False, **kwargs: Any) -> None:
    """Print a message to the console by joining the positional arguments
    `msg` with spaces.

    `echo` is meant for messages that explain to the user what spin is doing
    (e.g. *echoing* commands launched). It will remain silent though when ``spin``
    is run with the ``--quiet`` flag. If the parameter ``resolve`` is set to
    ``True``, the arguments are interpolated against the configuration tree.

    `echo` supports the same keyword arguments as Click's :py:func:`click.echo`.

    """
    if CONFIG.verbosity > Verbosity.QUIET:
        if resolve:
            msg = interpolate(msg)  # type: ignore[assignment]
        msg = obfuscate(msg)  # type: ignore[assignment]
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
    if CONFIG.verbosity > Verbosity.NORMAL:
        msg = interpolate(msg)  # type: ignore[assignment]
        msg = obfuscate(msg)  # type: ignore[assignment]
        click.echo(click.style("spin: ", fg="green"), nl=False)
        click.echo(" ".join(msg), **kwargs)


def debug(*msg: str, resolve: bool = False, **kwargs: Any) -> None:
    """Print a message to the console by joining the positional arguments
    `msg` with spaces.

    Arguments are interpolated against the configuration tree if ``resolve``
    evaluates to ``True``. `debug` will remain silent unless ``spin`` is run
    with the ``-vv`` flag. `debug` is meant for messages that provide internal
    details.

    `debug` supports the same keyword arguments as Click's
    :py:func:`click.echo`.

    """
    if CONFIG.verbosity > Verbosity.INFO:
        if resolve:
            msg = interpolate(msg)  # type: ignore[assignment]
        msg = obfuscate(msg)  # type: ignore[assignment]
        click.echo(click.style("spin: debug: ", fg="white", dim=True), nl=False)
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
    msg = obfuscate(msg)  # type: ignore[assignment]
    click.echo(click.style("spin: warning: ", fg="yellow"), nl=False, err=True)
    click.echo(" ".join(msg), err=True, **kwargs)


def error(*msg: str, resolve: bool = True, **kwargs: Any) -> None:
    """Print an error message to the console by joining the positional
    arguments `msg` with spaces.

    Arguments are interpolated against the configuration tree if `resolve`
    evaluates to `True`. The output is written to standard error.

    `error` supports the same keyword arguments as Click's
    :py:func:`click.echo`.

    """
    if resolve:
        msg = interpolate(msg)  # type: ignore[assignment]
    msg = obfuscate(msg)  # type: ignore[assignment]
    click.echo(click.style("spin: error: ", fg="red"), nl=False, err=True)
    click.echo(" ".join(msg), err=True, **kwargs)


def confirm(*msg: str, resolve: bool = True, **kwargs: Any) -> bool:
    """Prompt user for confirmation.

    Arguments are interpolated against the configuration tree if `resolve`
    evaluates to `True`. The output is written to standard out.

    `confirm` supports the same keyword arguments as Click's
    :py:func:`click.confirm`.

    """
    if resolve:
        msg = interpolate(msg)  # type: ignore[assignment]
    msg = obfuscate(msg)  # type: ignore[assignment]
    click.echo(click.style("spin: ", fg="yellow"), nl=False)
    return click.confirm(" ".join(msg), **kwargs)


class Verbosity(IntEnum):
    """
    :py:class:`enum.IntEnum` defining four verbosity levels:

    * ``QUIET``: Outputs only warnings and errors via :py:func:`csspin.warn()` and
      :py:func:`csspin.error()`.
    * ``NORMAL``: Outputs the normal amount of verbosity, extending the quiet
      level by enabling :py:func:`csspin.echo()`.
    * ``INFO``: Extends normal verbosity to enable :py:func:`csspin.info()`.
    * ``DEBUG``: Extends info verbosity to enable debug messages via
      :py:func:`csspin.debug()`.
    """

    QUIET = -1
    NORMAL = 0
    INFO = 1
    DEBUG = 2

    @classmethod
    def _missing_(cls, _) -> Verbosity:  # type: ignore[no-untyped-def]
        warn(
            "Invalid verbosity level, only '-v' and '-vv' are allowed! Verbosity is"
            " set to 'DEBUG'."
        )
        return Verbosity(2)


class DirectoryChanger:
    """A simple class to change the current directory.

    Change directory on construction, and restore the cwd when used as
    a context manager. Noop if we're already in the wanted directory.
    """

    def __init__(self: DirectoryChanger, path: str | Path) -> None:
        """Change directory."""
        path = interpolate1(path)
        self._cwd = os.getcwd()
        if not os.path.samefile(path, self._cwd):
            echo("cd", path)
            os.chdir(path)

    def __enter__(self: DirectoryChanger) -> None:
        """Nop."""

    def __exit__(self: DirectoryChanger, *args: Any) -> None:
        """Change back to where we came from."""
        if not os.path.samefile(self._cwd, os.getcwd()):
            echo("cd", self._cwd)
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
        <do something in this directory>

    """
    return DirectoryChanger(path)


def exists(path: str | Path) -> bool:
    """Check whether `path` exists. The argument is interpolated against
    the configuration tree.

    """
    path = interpolate1(path)
    return os.path.exists(path)


def normpath(*args: str | Path) -> str:
    """Interpolate and return a normalized path as str"""
    return os.path.normpath(os.path.join(*interpolate(args)))  # type: ignore[no-any-return]


def abspath(*args: str | Path) -> str:
    """Interpolate and return an absolute path as str"""
    return os.path.abspath(normpath(*args))


def mkdir(path: str | Path) -> str:
    """Ensure that `path` exists.

    If necessary, directories are recursively created to make `path`
    available. The argument is interpolated against the configuration
    tree.

    """
    if not exists(path := interpolate1(Path(path))):
        echo("mkdir -p", path)
        os.makedirs(path)
    return path


def rmtree(path: str | Path) -> None:
    """Recursively remove `path` and everything it contains.
    Can also remove single files. The argument
    is interpolated against the configuration tree.

    Obviously, this should be used with care.

    """
    if (path := interpolate1(path)) and not exists(path):
        return
    if sys.platform == "win32":
        echo(f"rm {path} -recurse -force")
    else:
        echo(f"rm -rf {path}")

    if (path := Path(path)).is_dir():
        path.rmtree()
    else:
        path.remove()


def mv(source: str | Path, target: str | Path) -> None:
    """Move a file or directory recursively from `source` to `target` in case
    the `target` exists, otherwise rename `source` to `target`.

    """
    if not exists((source := str(interpolate1(source)))):
        die(f"{source} does not exist!")
    target = str(interpolate1(target))

    if sys.platform == "win32":
        echo(f"move-item -path {source} -destination {target}")
    else:
        echo(f"mv {source} {target}")

    shutil.move(source, target)


def copy(source: str | Path, target: str | Path) -> None:
    """Copy a file or directory recursively from `source` to `target` in case
    the `target` exists.

    """
    if not exists((source := Path(interpolate1(source)).absolute())):
        die(f"{source} does not exist!")
    target = Path(interpolate1(target)).absolute()

    source_is_dir = source.is_dir()
    if sys.platform == "win32":
        opts = "-recurse" if source_is_dir else ""
        echo(f"copy-item -path {source} -destination {target} {opts}")
    else:
        opts = "-r " if source_is_dir else ""
        echo(f"cp {opts}{source} {target}")

    if source_is_dir:
        source.copytree(
            (target / source.basename()).mkdir_p(),
            dirs_exist_ok=True,
        )
    else:
        source.copy2(target)


def die(*msg: Any, resolve: bool = True) -> None:
    """Terminates ``spin`` with a non-zero return code and print the error
    message `msg`.

    Arguments are interpolated against the configuration tree if `resolve`
    evaluates to `True`.

    """
    if resolve:
        msg = interpolate(msg)  # type: ignore[assignment]
    error(*msg, resolve=False)
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


def sh(*cmd: Any, **kwargs: Any) -> subprocess.CompletedProcess | None:
    """Run a program by building a command line from `cmd`.

    When multiple positional arguments are given, each is treated as
    one element of the command. When just one positional argument is
    used, `sh` assumes it to be a single command and splits it into
    multiple arguments using :py:func:`shlex.split`. The `cmd`
    arguments are interpolated against the configuration tree. When
    `silent` is ``False``, the resulting command line will be
    echoed. When `shell` is ``True``, the command line is passed to
    the system's shell.

    Other keyword arguments are passed into
    :py:func:`subprocess.run`.

    All positional arguments are interpolated against the
    configuration tree.

    >>> sh("ls", "{HOME}")

    """
    cmd = interpolate(cmd)  # type: ignore[assignment]
    shell = kwargs.pop("shell", len(cmd) == 1)
    check = kwargs.pop("check", True)
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

    message = "Command '{cmd_}' failed with exit status {returncode}."
    cmd_ = cmd if isinstance(cmd, str) else subprocess.list2cmdline(cmd)  # type: ignore[unreachable] # noqa: E501
    try:
        debug(
            f"subprocess.run({cmd}, shell={shell}, check={check}, env={argenv},"
            f" executable={executable}, kwargs={kwargs}",
        )
        cpi = subprocess.run(
            cmd, shell=shell, check=check, env=env, executable=executable, **kwargs
        )
    except FileNotFoundError as ex:
        debug(format_exc())
        die(str(ex))
    except subprocess.CalledProcessError as ex:
        debug(format_exc())
        if check:
            die(message.format(cmd_=cmd_, returncode=ex.returncode))
        cpi = subprocess.CompletedProcess(args=cmd, returncode=ex.returncode)

    if not check and cpi.returncode:
        warn(message.format(cmd_=cmd, returncode=cpi.returncode))

    return cpi


def backtick(*cmd: str, **kwargs: Any) -> str:
    kwargs["stdout"] = subprocess.PIPE
    cpi = sh(*cmd, **kwargs)
    return cpi.stdout.decode()  # type: ignore[no-any-return,union-attr]


#: EXPORTS is a list that contains all (key, value) tuples of environment variables
#: that got set or unset via :py:func:`csspin.setenv` during the current spin execution.
#:
#: The ``value`` of a given element is already fully interpolated, except for
#: parts that look like environment variables. So any plugin using ``EXPORTS`` is able
#: to lazily evaluate the value of a variable in cases, where it has been set
#: multiple times.
#:
#: A case where that's relevant can be seen in the following example:
#:
#: Example:
#:
#: >>> os.environ.getenv("PATH")
#: "/usr/bin:/bin"
#: >>> setenv(PATH="{spin.project_root}/bin:{PATH}")
#: >>> setenv(PATH="{python.scriptdir}:{PATH}")
#: >>> EXPORTS
#: [("PATH", "/home/foo/project/bin:{PATH}"), ("PATH", "/home/foo/project/.spin/venv/bin:{PATH})]
#:
#: As can be seen, the real value of ``PATH`` should be
#: ``"/home/foo/project/.spin/venv/bin:/home/foo/project/bin:"/usr/bin:/bin"``,
#: which any plugin could now generate.
EXPORTS: list[tuple[str, str]] = []


def setenv(*args: Any, **kwargs: Any) -> None:
    """Set or unset one or more environment variables. The values of
    keyword arguments are interpolated against the configuration tree.

    Passing ``None`` as a value removes the environment variable.

    Variables that have been set during or before ``configure()`` will be
    patched into the activation scripts of the Python virtual environment.

    On Windows, all passed environment variable keys will be set in upper case.

    >>> setenv(FOO="{foo.bar}", BAZ="some-value")

    """

    def _value_replacement_for_echoing(value: str) -> str:
        keys = re.findall(r"{(?P<key>\w+?)}", value)
        if sys.platform == "win32":
            for key in keys:
                if key in os.environ:
                    value = value.replace(f"{{{key}}}", f"$env:{key}")
        else:
            for key in keys:
                if key in os.environ:
                    value = value.replace(f"{{{key}}}", f"${key}")
        return value

    for key, value in kwargs.items():
        if sys.platform == "win32":
            key = key.upper()

        if value is None:
            if not args:
                if sys.platform == "win32":
                    echo(f"$env:{key}=$null", resolve=False)
                else:
                    echo(f"unset {key}", resolve=False)
            os.environ.pop(key, None)
            EXPORTS.append((key, ""))
        else:
            interpolated_value = interpolate1(value)
            exports_value = interpolate1(value, interpolate_environ=False)
            if not args:
                value_to_print = _value_replacement_for_echoing(exports_value)
                if sys.platform == "win32":
                    echo(f'$env:{key}="{value_to_print}"', resolve=False)
                else:
                    echo(f"export {key}={value_to_print}", resolve=False)
            else:
                echo(args[0])
            os.environ[key] = interpolated_value
            EXPORTS.append((key, exports_value))


def _read_file(fn: str | Path, mode: str) -> str | bytes:
    fn = interpolate1(fn)
    with open(fn, mode, encoding="utf-8" if "b" not in mode else None) as f:
        return f.read()  # type: ignore[no-any-return]


def readlines(fn: str | Path) -> list[str]:
    fn = interpolate1(fn)
    with open(fn, "r", encoding="utf-8") as f:
        return f.readlines()


def writelines(fn: str | Path, lines: str) -> None:
    fn = interpolate1(fn)
    with open(fn, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _write_file(fn: str | Path, mode: str, data: bytes | str) -> int:
    fn = interpolate1(fn)
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


# On Windows platformdirs.user_config_dir and platformdirs.user_data_dir
# both point to %LOCALAPPDATA%, that's why we need /data and /config subfolders
os.environ["SPIN_CONFIG"] = os.environ.get(
    "SPIN_CONFIG",
    Path.joinpath(
        platformdirs.user_config_dir(),
        "spin",
        "config" if sys.platform == "win32" else "",
    ).normpath(),
)
os.environ["SPIN_DATA"] = os.environ.get(
    "SPIN_DATA",
    Path.joinpath(
        platformdirs.user_data_dir(), "spin", "data" if sys.platform == "win32" else ""
    ).normpath(),
)


def interpolate1(
    literal: str | Path, *extra_dicts: dict, interpolate_environ: bool = True
) -> str | Path:
    """
    Interpolate a string or path against the configuration tree and the
    environment.

    Example:

    >>> interpolate1("{SHELL}")
    '/usr/bin/zsh'

    If literal is not a string or path, it will be converted to a string prior
    interpolating.

    To avoid interpolation for literals or specific parts of a literal, curly
    braces can be used to escape curly braces, like regular f-string
    interpolation.

    Example:

    >>> interpolate1(
    ...     '{{"header": {{"language": "en", "data": "{SPIN_DATA}"}}}}'
    ... )
    '{"header": {"language": "en", "data": "/home/developer/.local/share/spin"}}'

    It may be necessary to omit the interpolation against the environment, in that case
    the parameter ``interpolate_environ`` can be set to ``False``.

    Example:

    >>> interpolate1("{spin.version} and {PATH}", interpolate_environ=False)
    "1.0.2.dev5 and {PATH}"

    .. Attention:: **Do not use** :py:func:`csspin.interpolate1` **in a plugins'
       top-level**, as the one can't rely on the configuration tree at import time
       of the module.

       .. code-block:: python
          :caption: Negative example: How not to use :py:func:`csspin.interpolate1`
          :linenos:

          from csspin import config, interpolate1

          defaults = config(key=interpolate1("{some.property}"))

    .. Attention:: If the interpolated property is not set, not NoneType but "None" as a string is returned.

    """
    is_path = isinstance(literal, Path)
    literal = str(literal)
    seen = set()
    previous = None

    where_to_look = collections.ChainMap(
        {"config": CONFIG},
        CONFIG,
        os.environ if interpolate_environ else {},
        *extra_dicts,
        *NSSTACK,  # type: ignore[arg-type]
    )

    while previous != literal:
        # Interpolate until we reach a fixpoint -- this allows for
        # nested variables.
        if literal in seen:
            die(
                f"Could not interpolate '{literal}' due to RecursionError.",
                resolve=False,
            )
        seen.add(previous := literal)

        # We need to protect double braces by doubling them, because
        # .format() converts {{}} to {} undependent of if it interpolated
        # something within these braces or not.
        literal = literal.replace("}}", "}}}}").replace("{{", "{{{{")
        try:
            if interpolate_environ:
                literal = literal.format_map(where_to_look)
            else:
                # When not interpolating the environ, we need to escape
                # sub-literals that look like environment variables.
                literal = re.sub(r"({\w+})", r"{\1}", literal)
                literal = literal.format_map(where_to_look)
                literal = re.sub(r"{({\w+})}", r"\1", literal)
        except KeyError as ex:
            error_key = str(ex)[1:-1]
            die(f"Cannot interpolate '{{{error_key}}}' in {literal}.", resolve=False)
        except AttributeError as ex:
            error_key = str(ex).replace("No property ", "")[1:-1]
            die(f"Cannot interpolate '{{{error_key}}}' in {literal}.", resolve=False)
    literal = literal.replace("{{", "{").replace("}}", "}")
    return Path(literal).normpath() if is_path else literal


def interpolate(literals: Iterable, *extra_dicts: dict) -> list:
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


def config(*args: Any | None, **kwargs: Any) -> ConfigTree:
    """`config` creates a configuration subtree:

    >>> config(a="alpha", b="beta)
    {"a": "alpha", "b": "beta}

    Plugins use `config` to declare their ``defaults`` tree.

    """

    from csspin.tree import ConfigTree

    return ConfigTree(*args, **kwargs, __ofs_frames__=1)  # type: ignore[arg-type]


def readyaml(fname: str | Path) -> ConfigTree:
    """Read a YAML file."""
    from csspin.tree import tree_load

    fname = interpolate1(fname)
    return tree_load(fname)


def download(url: str, location: str | Path) -> None:
    """Download data from ``url`` to ``location``."""
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
            ),
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

    * `aliases` is a list of aliases for the command (e.g. "tests" is
      an alias for "test")

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
    from csspin import cli  # pylint: disable=cyclic-import

    def task_wrapper(
        fn: Callable,
        group: GroupWithAliases = cli.commands,  # type: ignore[assignment]
    ) -> Callable:
        task_object = fn
        pass_context = False
        context_settings = config()
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())
        if param_names and "ctx" in param_names:
            pass_context = True
            task_object = click.pass_context(fn)
            param_names.pop(param_names.index("ctx"))
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
            task_object.full_name = " ".join((group.name, task_object.name))  # type: ignore[attr-defined]
        else:
            task_object.full_name = task_object.name  # type: ignore[attr-defined]
        if hook:
            cfg = get_tree()
            hook_tree = cfg.spin.get("hooks", config())
            hooks = hook_tree.setdefault(hook, [])
            hooks.append(task_object)
        for alias in aliases:
            group.register_alias(alias, task_object)

        def regular_callback(*args: Any, **kwargs: Any) -> Any:
            ensure(task_object)  # type: ignore[arg-type]
            return fn(*args, **kwargs)

        def alternate_callback(*args: Any, **kwargs: Any) -> Any:
            ensure(task_object)  # type: ignore[arg-type]
            return fn(get_tree(), *args, **kwargs)

        if pass_config and pass_context:
            task_object.callback = click.pass_context(alternate_callback)
        elif pass_config:
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
    from csspin import cli

    def group_decorator(fn: str | Path) -> Callable:

        noenv = kwargs.pop("noenv", False)
        kwargs["cls"] = cli.GroupWithAliases
        grp = cli.commands.group(*args, **kwargs)(click.pass_context(fn))  # type: ignore[attr-defined]
        if noenv:
            cli.register_noenv(grp.name)

        def subtask(*args: Any, **kwargs: Any) -> Callable:
            def task_decorator(fn: str | Path) -> click.Command:
                cmd = task(*args, **kwargs, group=grp)(fn)
                return cmd  # type: ignore[no-any-return]

            return task_decorator

        grp.task = subtask
        return grp  # type: ignore[no-any-return]

    return group_decorator


def getmtime(fn: str | Path) -> float:
    """Get the modification of file `fn`.

    `fn` is interpolated against the configuration tree.

    """
    return os.path.getmtime(interpolate1(fn))


def is_up_to_date(target: str | Path, sources: Iterable[str | Path]) -> bool:
    """Check whether `target` exists and is newer than all of the
    `sources`.

    """
    if not exists(target):
        return False
    if not isinstance(sources, Iterable):
        die(  # type: ignore[unreachable]
            f"Can't check if {target} is up to date, since 'sources' is not iterable."
        )
    target_mtime = getmtime(target)
    source_mtimes = [getmtime(src) for src in sources] + [0.0]
    return target_mtime >= max(source_mtimes)


def run_script(script: str | list, env: dict | None = None) -> None:
    """Run a list of shell commands."""
    if isinstance(script, str) or not isinstance(script, Iterable):
        script = [str(script)]
    for line in script:
        sh(line, shell=True, env=env)


def run_spin(script: str | list) -> None:
    """Run a list of spin commands."""
    from csspin.cli import commands

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
    if (target_def := cfg.build_rules.get(target, None)) is None:
        if not exists(target) and not phony:
            die(
                f"Sorry, I don't know how to produce '{target}'. You may want to"
                " add a rule to your spinfile.yaml in the 'build_rules'"
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


def ensure(command: click.Command) -> None:
    # Check 'command_name' for dependencies declared under
    # 'build_rules', and make sure to produce it. This is used
    # internally and intentionally undocumented.
    debug(f"checking preconditions for {command}")
    cfg = get_tree()
    build_target(cfg, f"task {command.full_name}", phony=True)  # type: ignore[attr-defined]


def invoke(hook: str, *args: Any, **kwargs: Any) -> None:
    '''``invoke()`` invokes the tasks that have the ``when`` hook
    `hook`. As an example, here is the implementation of **test**:

    .. code-block:: python

       @task(aliases=["tests"])
       def test(cfg, coverage: option("--coverage", "coverage", is_flag=True)):
           """Run all tests defined in this project"""
           invoke("test", coverage=coverage)

    The way a task that uses `invoke` is invoking other tasks is part of the
    call interface contract: *all* tasks initialized like ``@task(when="test")``
    *must* support the ``coverage`` argument as part of their Python function
    signature (albeit not necessarily the same command line flag
    ``--coverage``).
    '''
    ctx = click.get_current_context()
    cfg = get_tree()

    if not (hooks := cfg.spin.hooks.setdefault(hook, [])):
        warn(f"No tasks found for hook '{hook}'")
        return
    n_hooks = len(hooks)

    info(
        f"{hook} hook will invoke the following tasks: "
        + ", ".join([f"'{h.full_name}'" for h in hooks])
    )

    for i, task_object in enumerate(hooks):
        prefix = f"{hook} ({i + 1}/{n_hooks}) -"

        echo(f"{prefix} calling '{task_object.full_name}'")
        # Filter kwargs so that plugins don't need to provide
        # options, just for being able to get called by a workflow.
        task_opts = [
            param.name
            for param in task_object.params
            if isinstance(param, click.Option)
        ]
        pass_opts = {k: v for k, v in kwargs.items() if k in task_opts}

        ctx.invoke(task_object, *args, **pass_opts)
        info(f"{prefix} '{task_object.full_name}' done")


def toporun(cfg: ConfigTree, *fn_names: Any, reverse: bool = False) -> None:
    """Run plugin functions named in 'fn_names' in topological order."""
    plugins = cfg.spin.topo_plugins
    if reverse:
        plugins = reversed(plugins)
    for func_name in fn_names:
        debug(f"toporun: {func_name}")
        for pi_name in plugins:
            if pi_name == "csspin.builtin" and func_name in ("cleanup", "provision"):
                # Don't run the hook in spin.builtin, it's a task there and not
                # considered a plugin's hook.
                continue
            pi_mod = cfg.loaded[pi_name]
            initf = getattr(pi_mod, func_name, None)
            if initf:
                debug(f"  {pi_name}.{func_name}()")
                initf(cfg)


def main(*args: Any, **kwargs: Any) -> None:
    from csspin.cli import cli

    if not args:
        args = None  # type: ignore[assignment]
    cli.main(args, **kwargs)  # type: ignore[arg-type]


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
    return requires.get(keyname, [])  # type: ignore[no-any-return]
