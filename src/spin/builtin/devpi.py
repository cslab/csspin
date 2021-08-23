# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import (Command, config, exists, get_tree, interpolate1, readyaml,
                  setenv, sh, task)

defaults = config(
    formats=["bdist_wheel"],
    requires=[".virtualenv"],
    packages=["devpi-client", "keyring"],
)


def prepare_environment():
    setenv(DEVPI_VENV="{virtualenv.venv}", DEVPI_CLIENTDIR="{spin.spin_dir}/devpi")


@task()
def stage():
    """Upload project wheel to the staging area."""
    prepare_environment()
    data = {}
    devpi = Command("devpi")
    if exists("{spin.spin_dir}/devpi/current.json"):
        data = readyaml("{spin.spin_dir}/devpi/current.json")
    if data.get("index", "") != interpolate1("{devpi.stage}"):
        devpi("use", "-t", "yes", "{devpi.stage}")
    devpi("login", "{devpi.user}")
    python = os.path.abspath(get_tree().virtualenv.python)
    devpi("upload", "-p", python, "--no-vcs", "--formats={','.join(devpi.formats)}")


@task()
def devpi(cfg, args):
    """Run the 'devpi' command inside the project's virtual environment.

    All command line arguments are simply passed through to 'devpi'.

    """
    prepare_environment()
    if hasattr(cfg.devpi, "url"):
        sh("devpi", "use", cfg.devpi.url)
    if hasattr(cfg.devpi, "user"):
        sh("devpi", "login", cfg.devpi.user)

    sh("devpi", *args)
