# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""
This plugin provisions Python Egg requirements of a project.
"""

from spin import Command, config, memoizer

defaults = config(
    cmd="easy_install",
    opts=["-q", "--no-deps"],
    requires=config(spin=[".ce15"]),
    requirements=[],
    extra_index_url=None,
)


def venv_hook(cfg):
    opts = cfg.eggs.opts
    if cfg.eggs.extra_index_url:
        opts.extend(["-i", cfg.eggs.extra_index_url])
    einstall = Command(cfg.eggs.cmd, *opts)

    with memoizer("{python.venv}/eggs.memo") as m:
        for req in cfg.eggs.requirements:
            if not m.check(req):
                einstall("install", *req.split())
                m.add(req)
