# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import sh, task, toporun


@task("exec")
def exec_shell(args):
    if not args:
        args = ("{platform.shell}",)
    sh(*args)


@task()
def cleanup(cfg):
    """Call the 'cleanup' hook in all plugins.

    This is expected to eventually remove provisioned software
    (e.g. spin's Python interpreter, virtualenv etc.), but never
    remove user-supplied data.
    """
    toporun(cfg, "cleanup")
