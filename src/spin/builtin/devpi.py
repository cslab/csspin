# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin.api import (
    config,
    task,
    sh,
    setenv,
    exists,
    readyaml,
    get_tree,
    argument,
    Command,
    interpolate1,
)


defaults = config(formats=["bdist_wheel"])
requires = [".virtualenv"]
packages = ["devpi-client", "keyring"]


def prepare_environment():
    setenv(
        DEVPI_VENV="{virtualenv.venv}", DEVPI_CLIENTDIR="{spin.spin_dir}/devpi"
    )


@task
def stage():
    prepare_environment()
    data = {}
    devpi = Command("devpi")
    if exists("{spin.spin_dir}/devpi/current.json"):
        data = readyaml("{spin.spin_dir}/devpi/current.json")
    if data.get("index", "") != interpolate1("{devpi.stage}"):
        devpi("use", "-t", "yes", "{devpi.stage}")
    devpi("login", "{devpi.user}")
    python = os.path.abspath(get_tree().virtualenv.python)
    devpi(
        "upload",
        "-p",
        python,
        "--no-vcs",
        "--formats={','.join(devpi.formats)}",
    )


@task
def devpi(passthrough: argument(nargs=-1)):
    prepare_environment()
    sh("devpi", *passthrough)
