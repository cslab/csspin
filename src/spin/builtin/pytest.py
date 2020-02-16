# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import config, sh, task

defaults = config(
    requires=["virtualenv", "preflight"],
    packages=["pytest", "pytest-cov", "pytest-tldr"],
)


@task(when="test")
def pytest(args):
    """Run the 'pytest' command."""
    if not args:
        args = ["./tests"]
    sh(
        "{virtualenv.scriptdir}/pytest",
        "--cov=spin",
        "--cov=tests",
        "--cov-report=html",
        *args
    )
