# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import os

from spin import config, echo, sh, task

defaults = config(
    exe="cpplint",
    opts=[],
    extensions=[".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".i"],
    requires=config(spin=[".python", ".vcs"], python=["cpplint~=1.6.1"]),
)


@task(when="lint")
def cpplint(cfg, args):
    """Run the 'cpplint' command."""
    if c_files := [
        f for f in cfg.vcs.modified if os.path.splitext(f)[1] in cfg.cpplint.extensions
    ]:
        exts = f"--extensions={','.join(ext[1:] for ext in cfg.cpplint.extensions)}"
        sh("{cpplint.exe}", exts, *cfg.cpplint.opts, *c_files)
    else:
        echo("cpplint: no modified C/C++ files")
