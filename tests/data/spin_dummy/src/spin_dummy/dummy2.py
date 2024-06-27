# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""
A dummy plugin that checks for dependencies between plugins in the same
plugin-package.

NOTE: This plugin does not provide a schema.
"""

from spin import config, echo, task

defaults = config(
    dummy2="me",
    requires=config(
        spin=["spin_dummy.dummy"],
    ),
)


@task()
def dummy2(cfg):
    echo("This is spin's dummy2 plugin")
