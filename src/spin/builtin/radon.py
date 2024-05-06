# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import logging

from spin import config, option, sh, task

defaults = config(
    exe="radon",
    opts=["-n", "{radon.mi_treshold}"],
    mi_treshold="B",
    requires=config(
        spin=[".vcs"],
        python=["radon"],
    ),
)


# TODO(wen): is this actually linting? Not sure
@task(when="lint")
def radon(cfg, allsource: option("--all", "allsource", is_flag=True), args):
    """Run radon to measure code complexity."""
    files = args or cfg.vcs.modified
    files = [f for f in files if f.endswith(".py")]
    if allsource:
        files = ("{spin.project_root}/src", "{spin.project_root}/tests")
    if files:
        logging.debug(f"radon: Modified files: {files}")
        sh("{radon.exe}", "mi", *cfg.radon.opts, *files)
