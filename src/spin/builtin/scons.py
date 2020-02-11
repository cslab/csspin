# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin.api import config, sh, task

defaults = config(
    cmd="scons",
    opts=["-j{}".format(os.cpu_count() or 1)],
    requires=[".virtualenv"],
    packages=["scons", "pyyaml", "cpytoolchain", "cs.acetao-dev"]
)


@task()
def scons(cfg):
    """Run scons command"""
    sh("{scons.cmd}", *cfg.scons.opts)
