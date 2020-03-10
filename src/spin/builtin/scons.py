# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin import config, sh, task

defaults = config(
    cmd="scons",
    opts=[f"-j{os.cpu_count()}"],
    requires=[".virtualenv"],
    packages=["scons"],
)


@task()
def scons(cfg, args):
    """Run scons command"""
    cmd = "{scons.cmd}"
    if sys.platform.startswith("win32"):
        cmd += ".bat"
    sh(cmd, *cfg.scons.opts, *args)
