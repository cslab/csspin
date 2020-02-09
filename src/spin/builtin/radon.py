# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.api import argument, config, option, sh, task

defaults = config(opts=[], cmd="radon",)
requires = [".lint"]
packages = ["radon"]


@task(when="lint")
def radon(
    ctx,
    allsource: option("--all", "allsource", is_flag=True),
    passthrough: argument(nargs=-1),
):
    """Run radon to measure code complexity."""
    cfg = ctx.obj
    files = passthrough
    if not files:
        files = [f for f in cfg.vcs.modified if f.endswith(".py")]
    if allsource:
        files = (
            "{spin.project_root}/src",
            "{spin.project_root}/tests",
        )
    if files:
        sh("{radon.cmd}", "mi", *cfg.radon.opts, *files)
