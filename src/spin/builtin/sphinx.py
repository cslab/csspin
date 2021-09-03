# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import config, sh, task

defaults = config(
    docs="{spin.project_root}/docs",
    packages=[
        "sphinx",
    ],
    opts="-q",
)


@task()
def docs(cfg):
    sh("make -C {sphinx.docs} latexpdf 'SPHINXOPTS={sphinx.opts}' ")
