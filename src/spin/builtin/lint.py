# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import invoke, option, task


@task(aliases=["check"])
def lint(allsource: option("--all", "allsource", is_flag=True)):
    """Run all linters defined in this project."""
    invoke("lint", allsource=allsource)
