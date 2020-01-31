# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.plugin import task, invoke


@task(aliases=["tests"])
def test():
    """Run all tests defined in this project."""
    invoke("test")
