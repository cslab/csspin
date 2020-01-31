# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.plugin import config, sh, task, argument

defaults = config()

requires = [".virtualenv", ".lint"]
packages = ["flake8"]


@task(when="lint")
def flake8(files: argument(nargs=-1)):
    """Run flake8 to lint Python code."""
    if not files:
        files = (
            "{spin.project_root}/src",
            "{spin.project_root}/plugins",
        )

    sh("{virtualenv.bindir}/flake8", *files)
