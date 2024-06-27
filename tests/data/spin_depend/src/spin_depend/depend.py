# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""A dummy plugin package used to test dependencies between plugin packages"""

from spin import config, echo, task

defaults = config(foo="bar", requires=config(spin=["spin_dummy.dummy"]))


@task()
def depend(cfg):
    echo("This is spin's depend plugin")
