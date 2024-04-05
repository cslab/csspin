# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import shutil

from spin import config, sh, task

defaults = config(
    requires=config(
        spin=[".python"],
        python=["pre-commit"],
    ),
)


@task("pre-commit")
def pre_commit(cfg, args):
    sh("pre-commit", *args)


def provision(cfg):
    sh("pre-commit install")


def cleanup(cfg):
    if shutil.which("pre-commit"):
        sh("pre-commit uninstall")
