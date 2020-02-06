# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.api import config, sh, task, argument

defaults = config()

requires = [".virtualenv", ".lint"]
packages = ["flake8", "flake8-fixme"]


@task(when="lint")
def flake8(files: argument(nargs=-1)):
    """Run flake8 to lint Python code."""
    if not files:
        files = (
            "{spin.project_root}/src",
            "{spin.project_root}/plugins",
        )

    sh("flake8", *files)
