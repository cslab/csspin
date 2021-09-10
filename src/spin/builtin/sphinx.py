# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import config, option, sh, task

defaults = config(
    docs="{spin.project_root}/docs",
    packages=[
        "sphinx",
    ],
    opts="-qaE",
)


@task()
def docs(cfg, html: option("--html", "html", is_flag=True)):
    if html:
        sh("make -C {sphinx.docs} html 'SPHINXOPTS={sphinx.opts}' ")
    sh("make -C {sphinx.docs} latexpdf 'SPHINXOPTS={sphinx.opts}' ")
