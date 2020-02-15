# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.api import config, option, sh, task

defaults = config(
    opts=["-n", "{radon.mi_treshold}"],
    cmd="radon",
    mi_treshold="B",
    requires=[".lint"],
    packages=["radon"],
)


@task(when="lint")
def radon(
    cfg, allsource: option("--all", "allsource", is_flag=True), args,
):
    """Run radon to measure code complexity."""
    files = args
    if not files:
        files = [f for f in cfg.vcs.modified if f.endswith(".py")]
    if allsource:
        files = (
            "{spin.project_root}/src",
            "{spin.project_root}/tests",
        )
    if files:
        sh("{radon.cmd}", "mi", *cfg.radon.opts, *files)
