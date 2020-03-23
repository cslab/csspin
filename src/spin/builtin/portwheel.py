# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import (
    config,
    exists,
    sh,
    task,
)


defaults = config(
    opts=["--wheel"],
    sdksrc="sdk",
    requires=[".virtualenv"],
    packages=["portwheel", "cpytoolchain"],
)


@task()
def portwheel(cfg, args):
    files = args
    if not files:
        import glob
        files = glob.glob("*.yaml")
        print(files)
    if not exists(cfg.portwheel.sdksrc):
        sh("svn", "co", "https://svn.contact.de/svn/sdk/trunk", cfg.portwheel.sdksrc)
    sh("portwheel", "--sdksrc={portwheel.sdksrc}", *files, *cfg.portwheel.opts)
