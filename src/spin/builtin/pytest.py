# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
from spin import config, option, sh, task

defaults = config(
    requires=[".virtualenv", ".preflight"],
    packages=["pytest", "pytest-cov", "pytest-tldr"],
)


@task(when="test")
def pytest(instance: option("--instance", "instance"), args):
    """Run the 'pytest' command."""
    if not args:
        if os.path.isdir("./tests"):
            args = ["./tests"]
    if args:
        sh(
            "{virtualenv.scriptdir}/pytest",
            "--cov=spin",
            "--cov=tests",
            "--cov-report=html",
            *args
        )
