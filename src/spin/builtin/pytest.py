# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.api import config, sh, task, argument

defaults = config()

requires = [".virtualenv", ".test"]
packages = ["pytest", "pytest-cov", "pytest-tldr"]


@task(when="test")
def pytest(files: argument(nargs=-1)):
    sh("{virtualenv.bindir}/pytest", "--cov=spin", "--cov-report=html", *files)
