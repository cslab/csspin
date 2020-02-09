# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin.api import (
    Command,
    config,
    echo,
    exists,
    group,
    interpolate1,
    memoizer,
    rmtree,
    setenv,
    sh,
)

requires = [".python"]

defaults = config(
    venv="{spin.project_root}/{virtualenv.abitag}-{python.platform}",
    memo="{virtualenv.venv}/spininfo.memo",
    bindir=(
        "{virtualenv.venv}/bin"
        if sys.platform != "win32"
        else "{virtualenv.venv}"
    ),
    scriptdir=(
        "{virtualenv.venv}/bin"
        if sys.platform != "win32"
        else "{virtualenv.venv}/Scripts"
    ),
    python="{virtualenv.bindir}/python",
    pip="{virtualenv.scriptdir}/pip",
)


@group
def venv(ctx):
    pass


@venv.task
def info(ctx):
    echo("{virtualenv.venv}")


@venv.task
def rm(cfg):
    cleanup(cfg)


def init(cfg):
    # To get the ABI tag, we've to call into the target interpreter,
    # which is not the one running the spin program. Not super cool,
    # firing up the interpreter just for that is slow.
    cpi = sh(
        "{python.interpreter}",
        "-c",
        "from wheel.pep425tags import get_abi_tag; print(get_abi_tag())",
        capture_output=True,
        silent=True,
    )
    cfg.virtualenv.abitag = cpi.stdout.decode().strip()

    if not cfg.python.use and not exists(
        "{python.script_dir}/virtualenv{platform.exe}"
    ):
        # If we use Python provisioned by spin, add virtualenv if
        # necessary.
        sh("{python.interpreter} -m pip install virtualenv")

    virtualenv = Command("{python.interpreter}", "-m", "virtualenv", "-q")
    pip = Command("{virtualenv.pip}", "-q")

    if not exists("{virtualenv.venv}"):
        virtualenv("-p", "{python.interpreter}", "{virtualenv.venv}")

    with memoizer("{virtualenv.memo}") as m:

        def pipit(*req):
            if not m.check(req):
                pip("install", *req)
                m.add(req)

        for req in cfg.requirements:
            pipit(req)

        for plugin in cfg.topo_plugins:
            plugin_module = cfg.loaded[plugin]
            for req in getattr(plugin_module, "packages", []):
                pipit(req)

        pipit("-e", ".")

    # It is more useful to abspath virtualenv bindir before pushing it
    # onto the PATH, as anything run from a different directory will
    # not pick up the venv bin.
    if sys.platform == "win32":
        venvabs = os.pathsep.join(
            (
                os.path.abspath(interpolate1("{virtualenv.bindir}")),
                os.path.abspath(interpolate1("{virtualenv.scriptdir}")),
            )
        )
    else:
        venvabs = os.path.abspath(interpolate1("{virtualenv.bindir}"))
    setenv(
        f"set PATH={venvabs}{os.pathsep}$PATH",
        PATH=os.pathsep.join((f"{venvabs}", os.environ["PATH"])),
    )


def cleanup(cfg):
    if exists("{virtualenv.venv}"):
        rmtree("{virtualenv.venv}")
