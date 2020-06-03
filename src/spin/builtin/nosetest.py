# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import sys
import os

from spin import config, option, sh, task


defaults = config(
    cmd="nosetests",
    opts=["--logging-filter=-morepath"],
    coverage_opts=["--with-coverage"],
    requires=[".virtualenv", ".preflight"],
)


@task(when="test", aliases=["nosetests"])
def nosetest(
    cfg,
    instance: option("--instance", "instance"),
    coverage: option("--coverage", "coverage", is_flag=True),
    args,
):
    """Run the 'nosetest' command."""
    if not instance:
        instance = cfg.nosetest.instance

    nosetests = cfg.nosetest.cmd
    if sys.platform.startswith("win32"):
        nosetests += ".exe"
    nosetests = os.path.join(instance, "bin", nosetests)
    nosetests = " ".join(
        [
            nosetests,
            " ".join(cfg.nosetest.coverage_opts) if coverage else "",
            " ".join(cfg.nosetest.opts),
            " ".join(cfg.nosetest.tests),
        ]
    )
    sh(nosetests, *args)
