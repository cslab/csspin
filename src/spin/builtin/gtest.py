# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys
import warnings

from spin import config, option, sh, task

import wheel.pep425tags


defaults = config(requires=[".virtualenv", ".preflight"])


def get_bin_dir():
    warnings.filterwarnings("ignore", message="Config variable 'Py_DEBUG' is unset")
    try:
        bin_dir = "%s-%s" % (
            wheel.pep425tags.get_abi_tag(),
            wheel.pep425tags.get_platform(),
        )
    except TypeError:
        bin_dir = "%s-%s" % (
            wheel.pep425tags.get_abi_tag(),
            wheel.pep425tags.get_platform(wheel.__path__),
        )
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
        args = [""]
    for test in cfg.gtest.tests:
        if sys.platform.startswith("win32"):
            test += ".exe"
        test = os.path.join(get_bin_dir(), test)
        sh(test, *args)
