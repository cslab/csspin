# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import os

from spin import config, echo, sh, task

defaults = config(
    exe="cppcheck",
    opts=[f"-j{os.cpu_count()}"],
    extensions=[".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".i"],
    requires=config(
        spin=[".python", ".vcs"],
        # Hm. Thats not available on pypi.org.
        python=["cs.cppcheck-dev"],
    ),
)


@task(when="check")
def cppcheck(cfg, args):
    """Run the 'cppcheck' command."""
    if c_files := [
        f for f in cfg.vcs.modified if os.path.splitext(f)[1] in cfg.cppcheck.extensions
    ]:
        sh("{cppcheck.exe}", *cfg.cppcheck.opts, *c_files)
    else:
        echo("cppcheck: no modified C/C++ files")
