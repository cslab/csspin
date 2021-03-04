# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import invoke, option, task


@task()
def build(cfg):
    """
    Run all build tasks.
    """
    invoke("build")
