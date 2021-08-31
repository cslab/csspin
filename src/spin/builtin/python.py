# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import logging
import os
import sys

from spin import (
    cd,
    config,
    die,
    download,
    echo,
    exists,
    interpolate1,
    mkdir,
    namespaces,
    setenv,
    sh,
    task,
)

N = os.path.normcase


defaults = config(
    pyenv=config(
        url="https://github.com/pyenv/pyenv.git",
        path=N("{spin.userprofile}/pyenv"),
        cache=N("{spin.userprofile}/cache"),
        python_build=(N("{python.pyenv.path}/plugins/python-build/bin/python-build")),
    ),
    nuget=config(
        url="https://dist.nuget.org/win-x86-commandline/latest/nuget.exe",
        exe=N("{spin.userprofile}/nuget.exe"),
    ),
    version="3.8.5",
    plat_dir=N("{spin.userprofile}/{platform.tag}"),
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
    sh("python", "setup.py", *args, "bdist_wheel")


def pyenv_install(cfg):
    with namespaces(cfg.python):
        echo("Installing Python {version} to {inst_dir}")
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
        sh("{interpreter} -m pip install -q --upgrade pip wheel packaging")


def nuget_install(cfg):
    if not exists("{python.nuget.exe}"):
        download("{python.nuget.url}", "{python.nuget.exe}")
    setenv(NUGET_HTTP_CACHE_PATH=N("{spin.userprofile}/nugetcache"))
    sh(
        "{python.nuget.exe}",
        "install",
        "-verbosity",
        "quiet",
        "-o",
        N("{spin.userprofile}/{platform.tag}"),
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
    sh("{python.interpreter} -m pip install -q --upgrade pip wheel packaging")


def provision(cfg):
    if not cfg.python.use:
        if not exists("{python.interpreter}"):
            if sys.platform == "win32":
                nuget_install(cfg)
            else:
                # Everything (Linux and macOS) else uses pyenv
                pyenv_install(cfg)
        else:
            echo("Python {python.version} found at {python.interpreter}")


def configure(cfg):
    if cfg.python.use:
        cfg.python.interpreter = cfg.python.use


def init(cfg):
    if not cfg.python.use:
        logging.info("Checking for %s", interpolate1("{python.interpreter}"))
        if not exists("{python.interpreter}"):
            die(
                "No Python interpreter has been provisioned for this project.\n\n"
                "Spin longer auto-provisions dependencies in this release.\n"
                "You might want to run 'spin provision', or use the'--provision' flag"
            )
