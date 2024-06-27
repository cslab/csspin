# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""A simple dummy plugin used for testing cs.spin"""

from spin import config, echo, task

defaults = config(dummy="me")


@task()
def dummy(cfg):
    echo("This is spin's dummy plugin")
