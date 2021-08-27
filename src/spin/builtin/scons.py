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


@task(when="build")
def scons(cfg, args):
    """Run scons command"""
    cmd = "{scons.cmd}"
    args = list(args)
    if cfg.quiet:
        args.insert(0, "-s")
    if sys.platform.startswith("win32"):
        cmd += ".bat"
    sh(cmd, *cfg.scons.opts, *args)
