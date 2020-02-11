# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.api import argument, config, sh, task

defaults = config(
    requires=[".virtualenv", ".test"],
    packages=["pytest", "pytest-cov", "pytest-tldr"],
)


@task(when="test")
def pytest(files: argument(nargs=-1)):
    if not files:
        files = ["./tests"]
    sh(
        "{virtualenv.scriptdir}/pytest",
        "--cov=spin",
        "--cov-report=html",
        *files
    )
