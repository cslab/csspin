# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import sys
import os

from spin import config, option, sh, task


defaults = config(
    requires=[".virtualenv", ".preflight"],
)


@task(when="test", aliases=["nosetests"])
def nosetest(cfg,
             instance: option("--instance", "instance"),
             args):
    """Run the 'nosetest' command."""
    if not instance:
        instance = cfg.nosetest.instance

    nosetests = "nosetests"
    if sys.platform.startswith("win32"):
        nosetests += ".exe"
    nosetests = os.path.join(instance, "bin", nosetests)
    nosetests = " ".join(
        [nosetests,
         " ".join(cfg.nosetest.opts),
         " ".join(cfg.nosetest.tests)])
    sh(nosetests, *args)
