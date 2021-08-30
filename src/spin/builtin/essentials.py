# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import sh, task


@task("exec", add_help_option=False)
def exec_shell(args):
    """Run a shell command in the project context."""
    if not args:
        args = ("{platform.shell}",)
    sh(*args)
