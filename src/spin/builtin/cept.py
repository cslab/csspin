# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin import config, option, sh, task

defaults = config(
    cmd="cdbtest", opts=[], requires=[".virtualenv", ".preflight"],
    packages=["behave"]
)


@task(when="test", aliases=["acceptance"])
def cept(
    cfg,
    instance: option("--instance", "instance"),
    coverage: option("--coverage", "coverage", is_flag=True),
    args,
):
    """Run the acceptance tests."""
    if not instance:
        instance = cfg.cept.instance

    cept = cfg.cept.cmd
    if sys.platform.startswith("win32"):
        cept += ".exe"
    cept = os.path.join(instance, "bin", cept)
    cept = " ".join([cept, " ".join(cfg.cept.opts)])
    sh(cept, *args)
