# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.api import invoke, task


@task(aliases=["check"])
def lint():
    """Run all linters defined in this project."""
    invoke("lint")
