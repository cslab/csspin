# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""

``python``
==========

This plugin provisions the requested version of the Python
programming languages.

.. code-block:: yaml

   # Add 'python' to the plugin list
   plugins:
     - python

   # Request a specific version of Python
   python:
     version: 3.8.12

On Linux and macOS, Python is installed by compiling from source
(implying, that Python's build requirements must be installed). On
Windows, pre-built binaries are downloaded using `nuget`.

If `pyenv <https://github.com/pyenv/pyenv>`_ is installed and active,
Python versions are automatically shared with `pyenv`.

To skip provisioning of Python and use an already installed version,
:py:data:`python.use` can be set to the name or the full path of an
interpreter:

.. code-block:: sh

   $ spin -p python.use=/usr/local/bin/python ...

Note: `spin` will install or update certain packages of that
interpreter, thus write access is required.

Tasks
-----

.. click:: spin.builtin.python:python
   :prog: spin python

.. click:: spin.builtin.python:wheel
   :prog: spin wheel


Properties
----------

* :py:data:`python.version` -- must be set to choose the
  required Python version
* :py:data:`python.interpreter` -- path to the Python interpreter
* :py:data:`python.pip` -- path to `pip`

Note: don't use these properties when using `virtualenv`, they will
point to the base installation.

"""

import logging
import os
import re
import sys

from spin import (
    Path,
    backtick,
    cd,
    config,
    die,
    download,
    exists,
    info,
    interpolate1,
    mkdir,
    namespaces,
    parse_version,
    setenv,
    sh,
    task,
    warn,
)

N = Path


defaults = config(
    pyenv=config(
        url="https://github.com/pyenv/pyenv.git",
        path=N("{spin.cache}/pyenv"),
        cache=N("{spin.cache}/cache"),
        python_build=(N("{python.pyenv.path}/plugins/python-build/bin/python-build")),
    ),
    nuget=config(
        url="https://dist.nuget.org/win-x86-commandline/latest/nuget.exe",
        exe=N("{spin.cache}/nuget.exe"),
    ),
    version=None,
    plat_dir=N("{spin.cache}/{platform.tag}"),
    inst_dir=(
        N("{python.plat_dir}/python/{python.version}")
        if sys.platform != "win32"
        else N("{python.plat_dir}/python.{python.version}/tools")
    ),
    bin_dir=(
        N("{python.inst_dir}/bin") if sys.platform != "win32" else "{python.inst_dir}"
    ),
    script_dir=(
        N("{python.inst_dir}/bin")
        if sys.platform != "win32"
        else N("{python.inst_dir}/Scripts")
    ),
    interpreter=N("{python.bin_dir}/python{platform.exe}"),
    pip=N("{python.script_dir}/pip{platform.exe}"),
    use=None,
)


def system_requirements(cfg):
    # This is our little database of system requirements for
    # provisioning Python; spin identifies platforms by a tuple
    # composed of the distro id and version e.g. ("debian", 10).
    return [
        # We intentionally leave out Tk, as it pulls in a lot of
        # graphics and X packages
        (
            lambda distro, version: distro in ("debian", "mint", "ubuntu"),
            {
                "apt-get": (
                    "git make build-essential libssl-dev zlib1g-dev libbz2-dev"
                    " libreadline-dev libsqlite3-dev curl libncursesw5-dev"
                    " xz-utils libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev"
                ),
            },
        ),
        (
            lambda distro, version: (
                distro in ("centos", "fedora")
                and not (distro == "fedora" and version >= parse_version("22"))
            ),
            {
                "yum": (
                    "git gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite"
                    " sqlite-devel openssl-devel libffi-devel xz-devel"
                ),
            },
        ),
        (
            lambda distro, version: (
                distro == "fedora" and version >= parse_version("22")
            ),
            {
                "dnf": (
                    "git make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite"
                    " sqlite-devel openssl-devel libffi-devel xz-devel"
                ),
            },
        ),
        (
            lambda distro, version: distro == "darwin",
            {
                "brew": "git openssl readline sqlite3 xz zlib",
            },
        ),
        (
            # FIXME: no idea, whether this makes any sense
            lambda distro, version: distro == re.match("opensuse", distro),
            {
                "zypper": (
                    "git gcc automake bzip2 libbz2-devel xz xz-devel openssl-devel"
                    " ncurses-devel readline-devel zlib-devel libffi-devel"
                    " sqlite3-devel"
                ),
            },
        ),
        (
            # FIXME: no idea, whether this makes any sense
            lambda distro, version: distro == "rhel",
            {
                "yum": (
                    "gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite"
                    " sqlite-devel openssl-devel libffi-devel xz-devel"
                )
            },
        ),
    ]


@task()
def python(args):
    """Run the Python interpreter used for this projects.

    Provisioning happens automatically. The 'python' task makes sure
    the requested Python release is installed.
    """
    sh("{python.interpreter}", *args)


@task(when="package")
def wheel(cfg):
    args = []
    if cfg.quiet:
        args = ["-q"]
    sh(
        "python",
        "setup.py",
        *args,
        "build",
        "-b",
        "{spin.env_base}/build",
        "bdist_wheel",
        "-d",
        "{spin.env_base}/dist",
    )


def pyenv_install(cfg):
    with namespaces(cfg.python):
        if "PYENV_ROOT" in os.environ or "PYENV_SHELL" in os.environ:
            info("Using your existing pyenv installation ...")
            sh("pyenv install --skip-existing {version}")
            sh(
                "python",
                "-mpip",
                "install",
                cfg.quietflag,
                "-U",
                "pip",
                "packaging",
            )
        else:
            info("Installing Python {version} to {inst_dir}")
            # For Linux/macOS using the 'python-build' plugin from
            # pyenv is by far the most robust way to install a
            # version of Python.
            if not exists("{pyenv.path}"):
                sh("git clone {pyenv.url} {pyenv.path}")
            else:
                with cd("{pyenv.path}"):
                    sh("git pull")
            # we should set
            setenv(PYTHON_BUILD_CACHE_PATH=mkdir("{pyenv.cache}"))
            setenv(PYTHON_CFLAGS="-DOPENSSL_NO_COMP")
            sh("{pyenv.python_build} {version} {inst_dir}")
            sh(
                "{interpreter}",
                "-mpip",
                "install",
                cfg.quietflag,
                "-U",
                "pip",
                "wheel",
                "packaging",
            )


def nuget_install(cfg):
    if not exists("{python.nuget.exe}"):
        download("{python.nuget.url}", "{python.nuget.exe}")
    setenv(NUGET_HTTP_CACHE_PATH=N("{spin.cache}/nugetcache"))
    sh(
        "{python.nuget.exe}",
        "install",
        "-verbosity",
        "quiet",
        "-o",
        N("{spin.cache}/{platform.tag}"),
        "python",
        "-version",
        "{python.version}",
    )
    paths = interpolate1("{python.inst_dir};" + N("{python.inst_dir}/Scripts"))
    setenv(
        f"set PATH={paths}{os.pathsep}$PATH",
        PATH=os.pathsep.join((f"{paths}", os.environ["PATH"])),
    )
    sh("{python.interpreter} -m ensurepip --upgrade")
    sh(
        "{python.interpreter}",
        "-mpip",
        "install",
        cfg.quietflag,
        "-U",
        "pip",
        "wheel",
        "packaging",
    )


def check_python_interpreter(cfg):
    try:
        pi = sh("{python.interpreter}", "--version", check=False, may_fail=True)
        return pi.returncode == 0
    except Exception:
        return False


def provision(cfg):
    info("Checking {python.interpreter}")
    if not check_python_interpreter(cfg):
        if sys.platform == "win32":
            nuget_install(cfg)
        else:
            # Everything else (Linux and macOS) uses pyenv
            pyenv_install(cfg)


def configure(cfg):
    if not cfg.python.version:
        die(
            "Spin's Python plugin no longer sets a default version.\n"
            "Please choose a version in spinfile.yaml by setting python.version"
        )
    # FIXME: refactor the pyenv check, as it also used elsewhere
    if cfg.python.use:
        warn("python.version will be ignored, using '{python.use}' instead")
        cfg.python.interpreter = cfg.python.use
    elif "PYENV_ROOT" in os.environ or "PYENV_SHELL" in os.environ:
        setenv(PYENV_VERSION="{python.version}")
        # FIXME: this fails if there is pyenv installed, but PATH has
        # another python before the pyenv shim
        # cfg.python.use = "python"
        # cfg.python.interpreter = cfg.python.use
        cfg.python.interpreter = backtick("pyenv which python").strip()


def init(cfg):
    if not cfg.python.use:
        logging.debug("Checking for %s", interpolate1("{python.interpreter}"))
        if not exists("{python.interpreter}"):
            die(
                "No Python interpreter has been provisioned for this project.\n\n"
                "Spin no longer auto-provisions dependencies in this release.\n"
                "You might want to run 'spin provision', or use the'--provision' flag"
            )
