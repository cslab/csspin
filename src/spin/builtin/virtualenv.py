# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.plugin import (
    config,
    sh,
    exists,
    rmtree,
    memoizer,
    group,
    echo,
    Command,
)

requires = [".python"]

defaults = config(
    venv="{spin.project_root}/{virtualenv.abitag}-{python.platform}",
    memo="{virtualenv.venv}/spininfo.memo",
    command="{python.bin_dir}/virtualenv",
    bindir="{virtualenv.venv}/bin",
    python="{virtualenv.bindir}/python",
    pip="{virtualenv.bindir}/pip",
)


@group
def venv(ctx):
    pass


@venv.task
def info(ctx):
    echo("{virtualenv.venv}")


@venv.task
def rm(ctx):
    cleanup(ctx.obj)


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

    if not exists("{virtualenv.command}"):
        sh("{python.pip} install virtualenv")

    virtualenv = Command("{virtualenv.command}", "-q")
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

        pipit("-e", ".")


def cleanup(cfg):
    if exists("{virtualenv.venv}"):
        rmtree("{virtualenv.venv}")
