# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin.api import (
    argument,
    config,
    download,
    echo,
    exists,
    interpolate1,
    mkdir,
    namespaces,
    rmtree,
    setenv,
    sh,
    task,
)

from wheel import pep425tags


# Thank you PyPA, you just broke an API
# https://github.com/pypa/wheel/commit/b5733b86155c696274564e86c2a5f966f9abbebf
try:
    pep425_platform = pep425tags.get_platform()
except TypeError:
    pep425_platform = pep425tags.get_platform(None)


defaults = config(
    pyenv=config(
        url="https://github.com/pyenv/pyenv.git",
        path="{spin.userprofile}/pyenv",
        cache="{spin.userprofile}/cache",
        python_build=(
            "{python.pyenv.path}/plugins/python-build/bin/python-build"
        ),
    ),
    nuget=config(
        url="https://dist.nuget.org/win-x86-commandline/latest/nuget.exe",
        exe="{spin.userprofile}/nuget.exe",
    ),
    version="3.8.1",
    platform=pep425_platform,
    plat_dir="{spin.userprofile}/{python.platform}",
    inst_dir=(
        "{python.plat_dir}/python/{python.version}"
        if sys.platform != "win32"
        else "{python.plat_dir}/python.{python.version}/tools"
    ),
    bin_dir=(
        "{python.inst_dir}/bin"
        if sys.platform != "win32"
        else "{python.inst_dir}"
    ),
    script_dir=(
        "{python.inst_dir}/bin"
        if sys.platform != "win32"
        else "{python.inst_dir}/Scripts"
    ),
    interpreter="{python.bin_dir}/python{platform.exe}",
    use=None,
)


@task
def python(passthrough: argument(nargs=-1)):
    """Run the Python interpreter used for this projects.

    Provisioning happens automatically. The 'python' task makes sure
    the requested Python release is installed.
    """
    sh("{python.interpreter}", *passthrough)


def pyenv_install(cfg):
    with namespaces(cfg.python):
        echo("Installing Python {version} to {inst_dir}")
        # For Linux/macOS using the 'python-build' plugin from
        # pyenv is by far the most robust way to install a
        # version of Python.
        if not exists("{pyenv.path}"):
            sh("git clone {pyenv.url} {pyenv.path}")
        # we should set
        setenv(PYTHON_BUILD_CACHE_PATH=mkdir("{pyenv.cache}"))
        sh("{pyenv.python_build} {version} {inst_dir}")
        sh("{interpreter} -m pip install -q --upgrade pip wheel")


def nuget_install(cfg):
    if not exists("{python.nuget.exe}"):
        download("{python.nuget.url}", "{python.nuget.exe}")
    setenv(NUGET_HTTP_CACHE_PATH="{spin.userprofile}/nugetcache")
    sh(
        "{python.nuget.exe}",
        "install",
        "-verbosity",
        "quiet",
        "-o",
        "{spin.userprofile}/{python.platform}",
        "python",
        "-version",
        "{python.version}",
    )
    pathes = interpolate1("{python.inst_dir};" "{python.inst_dir}/Scripts")
    setenv(
        f"set PATH={pathes}{os.pathsep}$PATH",
        PATH=os.pathsep.join((f"{pathes}", os.environ["PATH"])),
    )
    sh("{python.interpreter} -m ensurepip")
    sh("{python.interpreter} -m pip install -q --upgrade pip wheel")


def init(cfg):
    if not cfg.python.use:
        mkdir("{spin.userprofile}")
        if not exists("{python.interpreter}"):
            if sys.platform == "win32":
                nuget_install(cfg)
            else:
                # Everything (Linux and macOS) else uses pyenv
                pyenv_install(cfg)


def cleanup(cfg):
    if not cfg.python.use:
        if exists("{python.plat_dir}"):
            rmtree("{python.plat_dir}")


def configure(cfg):
    if cfg.python.use:
        cfg.python.interpreter = cfg.python.use
