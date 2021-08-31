# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import config, sh, task

defaults = config(requires=[".virtualenv"], packages=["pre-commit"])


@task("pre-commit")
def pre_commit(cfg, args):
    sh("pre-commit", *args)


def provision(cfg):
    sh("pre-commit install")
