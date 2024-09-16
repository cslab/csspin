# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/
#

from spin import echo, task


@task()
def demo(cfg):
    echo("This is spin's demo plugin")
