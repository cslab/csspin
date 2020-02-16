# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import sh, task, toporun


@task("exec")
def exec_shell(args):
    """Run a shell command in the project context."""
    if not args:
        args = ("{platform.shell}",)
    sh(*args)


@task()
def cleanup(cfg):
    """Call the 'cleanup' hook in all plugins.

    'cleanup' eventually reverses what provisioning has done before by
    removing what has been provisioned by plugins. E.g. the Python
    interpreter provisioned by the built-in 'python' plugin, or the
    virtual environment created for the project.

    'cleanup' should never remove user-supplied files that cannot be
    re-provisioned (unless you're using ill behaved plugins, that is
    ...)

    """
    toporun(cfg, "cleanup")
