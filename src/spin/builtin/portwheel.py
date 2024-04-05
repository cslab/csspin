# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

from spin import config, exists, option, sh, task

defaults = config(
    opts=["--wheel"],
    sdksrc="sdk",
    requires=config(
        spin=[".python"],
        python=["portwheel", "cpytoolchain"],
    ),
)


@task()
def portwheel(cfg, sdksrc: option("--sdksrc", "sdksrc"), args):
    files = args
    if not files:
        import glob

        files = glob.glob("*.yaml")
        print(files)
    if not sdksrc:
        sdksrc = cfg.portwheel.sdksrc
    if not exists(sdksrc):
        sh("svn", "co", "https://svn.contact.de/svn/sdk/trunk", sdksrc)
    sh("portwheel", f"--sdksrc={sdksrc}", *cfg.portwheel.opts, *files)
