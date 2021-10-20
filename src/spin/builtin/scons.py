# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, setenv, sh, task

defaults = config(
    cmd="scons",
    opts=[f"-j{os.cpu_count()}"],
    requires=config(
        spin=[".python"],
        python=["scons"],
    ),
    cache_vcvars=False,
)


@task(when="build")
def scons(cfg, args):
    """Run scons command"""
    cmd = "{scons.cmd}"
    args = list(args)
    if cfg.quiet:
        args.insert(0, "-s")
    setenv(SCONS_CACHE_MSVC_CONFIG=str(cfg.scons.cache_vcvars))
    sh(cmd, *cfg.scons.opts, *args)
