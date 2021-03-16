# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, option, sh, task

defaults = config(
    cmd="flake8",
    opts=["--exit-zero", f"-j{os.cpu_count()}"],
    requires=[".virtualenv", ".vcs", ".preflight"],
    # These are the flake8 plugins we want to use. Maybe this should
    # be configurable in spinfile (candidates are "flake8-spellcheck"
    # or "flake8-cognitive-complexity", "dlint", "flake8-bandit" etc.)
    packages=[
        "flake8",
        # "flake8-import-order",
        "flake8-isort",
        "flake8-comprehensions",
        "flake8-copyright",
        "flake8-polyfill",
        # These are not Py2-compatible; dont use them by default, as
        # they would break the flake8 task on Py2. Users which are
        # Py3-only may get them via overwriting the
        # "packages"-property in thier spinfile
        #
        # "flake8-fixme",
        # "flake8-bugbear",
    ],
)


@task(when="lint")
def flake8(
    cfg,
    allsource: option("--all", "allsource", is_flag=True),
    coverage: option("--coverage", "coverage", is_flag=True),
    args,
):
    """Run flake8 to lint Python code."""
    files = args
    if not files:
        files = [f for f in cfg.vcs.modified if f.endswith(".py")]
    if allsource:
        files = ("{spin.project_root}/src", "{spin.project_root}/tests")
    if files:
        sh("{flake8.cmd}", *cfg.flake8.opts, *files)
