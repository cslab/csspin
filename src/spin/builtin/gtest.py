# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys
import warnings

from spin import config, interpolate1, option, sh, task

defaults = config(
    requires=[".python", ".preflight"],
    opts=["--gtest_brief=1", "--gtest_color=yes"],
)


def get_bin_dir():
    warnings.filterwarnings("ignore", message="Config variable 'Py_DEBUG' is unset")
    bin_dir = os.path.join(interpolate1("{python.scriptdir}"), "tests")
    return bin_dir


@task(when="test", aliases=["gtests"])
def gtest(
    cfg,
    instance: option("--instance", "instance"),
    coverage: option("--coverage", "coverage", is_flag=True),
    args,
):
    """Run the 'gtest' command."""
    if not args:
        args = cfg.gtest.opts
    for test in cfg.gtest.tests:
        if sys.platform.startswith("win32"):
            test += ".exe"
        test = os.path.normpath(os.path.join(get_bin_dir(), test))
        sh(test, *args)
