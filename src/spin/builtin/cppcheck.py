# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, sh, task

defaults = config(
    cmd="cppcheck",
    opts=[f"-j{os.cpu_count()}"],
    extensions=[".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".i"],
    requires=config(
        spin=[".python", ".vcs", ".preflight"],
        python=["cs.cppcheck-dev"],
    ),
)


@task(when="check")
def cppcheck(cfg, args):
    """Run the 'cppcheck' command."""
    c_files = [
        f for f in cfg.vcs.modified if os.path.splitext(f)[1] in cfg.cppcheck.extensions
    ]
    if c_files:
        print(c_files)
        cmd = "{cppcheck.cmd}"
        c_files_str = " ".join(c_files)
        cmd = " ".join([cmd, " ".join(cfg.cppcheck.opts), c_files_str])
        sh(cmd)
    else:
        print("cppcheck: no modified C/C++ files")
