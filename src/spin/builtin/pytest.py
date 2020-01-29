# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.plugin import config, sh, task, argument

defaults = config()

requires = [".virtualenv", ".test"]


@task(when="test")
def pytest(files: argument(nargs=-1)):
    sh("{virtualenv.bindir}/pytest", *files)
    pass


def configure(cfg):
    cfg.requirements.append("pytest")
