# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.plugin import (
    config,
    task,
    sh,
    echo,
    exists,
    setenv,
    rmtree,
    namespaces,
    argument,
    mkdir,
)
from wheel import pep425tags


# Thank you PyPA, you just broke an API
# https://github.com/pypa/wheel/commit/b5733b86155c696274564e86c2a5f966f9abbebf
try:
    pep425_platform = pep425tags.get_platform()
except TypeError:
    pep425_platform = pep425tags.get_platform(None)


# https://dist.nuget.org/win-x86-commandline/latest/nuget.exe


defaults = config(
    pyenv=config(
        url="https://github.com/pyenv/pyenv.git",
        path="{spin.userprofile}/pyenv",
        cache="{spin.userprofile}/cache",
        python_build=(
            "{python.pyenv.path}/plugins/python-build/bin/python-build"
        ),
    ),
    version="3.8.1",
    platform=pep425_platform,
    inst_dir="{spin.userprofile}/{python.platform}/python/{python.version}",
    bin_dir="{python.inst_dir}/bin",
    interpreter="{python.bin_dir}/python",
    use=None,
)


@task
def python(passthrough: argument(nargs=-1)):
    """Run the Python interpreter used for this projects.

    Provisioning happens automatically. The 'python' task makes sure
    the requested Python release is installed.
    """
    sh("{python.interpreter}", *passthrough)


def init(cfg):
    if not cfg.python.use:
        with namespaces(cfg.python):
            if not exists("{interpreter}"):
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


def cleanup(cfg):
    if not cfg.python.use:
        if exists("{python.inst_dir}"):
            rmtree("{python.inst_dir}")


def configure(cfg):
    if cfg.python.use:
        cfg.python.interpreter = cfg.python.use
