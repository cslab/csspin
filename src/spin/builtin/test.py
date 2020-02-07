# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.api import invoke, task


@task(aliases=["tests"])
def test():
    """Run all tests defined in this project."""
    invoke("test")
