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
    rmtree,
    namespaces,
    argument,
)
from wheel import pep425tags


defaults = config(
    pyenv=config(
        url="https://github.com/pyenv/pyenv.git",
        path="{spin.userprofile}/pyenv",
        python_build=(
            "{python.pyenv.path}/plugins/python-build/bin/python-build"
        ),
    ),
    platform=pep425tags.get_platform(),
    version="3.8.1",
    inst_dir="{spin.userprofile}/{python.platform}/python/{python.version}",
    bin_dir="{python.inst_dir}/bin",
    interpreter="{python.bin_dir}/python",
    pip="{python.bin_dir}/pip",
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
    if cfg.python.use:
        cfg.python.interpreter = cfg.python.use
    else:
        with namespaces(cfg.python):
            if not exists("{interpreter}"):
                echo("Installing Python {version} to {inst_dir}")
                if not exists("{pyenv.path}"):
                    sh("git clone {pyenv.url} {pyenv.path}")
                sh("{pyenv.python_build} {version} {inst_dir}")
                sh("{interpreter} -m pip install --upgrade pip")
                sh("{pip} install wheel")


def cleanup(cfg):
    if not cfg.python.use_existing:
        if exists("{python.inst_dir}"):
            rmtree("{python.inst_dir}")
