# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin import config, option, sh, task

defaults = config(
    cmd="mvn",
    goals=[],
    opts=[],
    defines={},
    pom_file="pom.xml",
    requires=[".virtualenv", ".java"],
    packages=[],
)


@task(when="build")
def maven(
    cfg,
    pom_file: option(
        "-f",
        "--file",
        show_default=(
            "Force the use of an alternate POM file " # noqa
            "(or directory with pom.xml)"
        ),
    ),
    defines: option(
        "-D",
        "--define",
        "defines",
        multiple=True,
        show_default="Define a system property", # noqa
    ),
    args,
):
    """Run maven command"""
    cmd = "{maven.cmd}"
    if sys.platform.startswith("win32"):
        cmd += ".cmd"
    opts = cfg.maven.opts
    # add pom file
    opts.append("-f")
    opts.append(pom_file or cfg.maven.pom_file)

    # add defines
    cfg_defines = cfg.maven.defines
    for d in defines:
        name, val = d.split("=")
        cfg_defines[name] = val

    for d in cfg_defines.items():
        opts.append("-D{}={}".format(*d))

    # do not use goals when some extra args are used
    if not args:
        opts.extend(cfg.maven.goals)
    sh(cmd, *opts, *args, env=os.environ)
