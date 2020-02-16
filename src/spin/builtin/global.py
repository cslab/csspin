# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import sys

import entrypoints

from spin import argument, group, memoizer, sh


@group("global")
def globalgroup(ctx):
    """Subcommands for managing globally available plugins."""
    pass


@globalgroup.task("add")
def global_add(packages: argument(nargs=-1)):
    cmd = [
        f"{sys.executable}",
        "-m",
        "pip",
        "install",
        # "-q",
        "-t",
        "{spin.plugin_dir}",
    ]
    with memoizer("{spin.spin_global_plugins}/packages.memo") as m:
        for pkg in packages:
            sh(*cmd, f"{pkg}")
            if not m.check(pkg):
                m.add(pkg)


@globalgroup.task("ls")
def global_ls():
    for ep in entrypoints.get_group_all("spin.plugin"):
        print(ep.__dict__)


@globalgroup.task("rm")
def global_rm():
    pass
