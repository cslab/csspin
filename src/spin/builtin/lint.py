# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin.plugin import task, invoke


@task
def lint():
    """Run all linters defined in this project."""
    invoke("lint")
