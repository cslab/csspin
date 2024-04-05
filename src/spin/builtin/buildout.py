# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import os
import shutil

from spin import config, option, sh, task

defaults = config(
    opts=["-q", "-N"],
    requires=config(
        spin=[".python"],
        python=["zc.buildout"],
    ),
)


@task()
def buildout(
    cfg,
    instance: option("--instance", "instance"),
    rebuild: option("--rebuild", is_flag=True),
    args,
):
    """Run the 'buildout' command."""
    if not instance:
        instance = cfg.buildout.instance
    if rebuild and os.path.isdir(instance):
        print(f"Deleting instance '{instance}'...")
        shutil.rmtree(instance)
    sh("buildout", *cfg.buildout.opts, "install", instance)
