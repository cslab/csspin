# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, sh, task


defaults = config(
    cmd="cpplint",
    opts=["--extensions=h,hh,hpp,c,cc,cpp,i"],
    extensions=[".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".i"],
    requires=[".virtualenv", ".vcs", ".preflight"],
    packages=["cpplint"],
)


@task(when="check")
def cpplint(cfg, args):
    """Run the 'cpplint' command."""
    c_files = [
        f for f in cfg.vcs.modified if os.path.splitext(f)[1] in cfg.cppcheck.extensions
    ]
    if c_files:
        print("cpplint: Modified files: ", c_files)
        cmd = "{cpplint.cmd}"
        c_files_str = " ".join(c_files)
        cmd = " ".join([cmd, " ".join(cfg.cpplint.opts), c_files_str])
        sh(cmd)
    else:
        print("cpplint: no modified C/C++ files")
