# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin.api import argument, config, sh, task

defaults = config(
    cmd="scons",
    opts=[f"-j{os.cpu_count()}"],
    requires=[".virtualenv"],
    packages=["scons"],
)


@task()
def scons(cfg, passthrough: argument(nargs=-1)):
    """Run scons command"""
    sh("{scons.cmd}", *cfg.scons.opts, *passthrough)
