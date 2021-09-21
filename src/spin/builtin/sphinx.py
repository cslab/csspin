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
    opts="-qaE",
    build_dir="{spin.env_base}/docs",
)


@task()
def docs(
    cfg,
    args,
):
    cmd = [
        "make",
        "-C",
        "{sphinx.docs}",
        "SPHINXOPTS={sphinx.opts}",
        "BUILDDIR={sphinx.build_dir}",
        "LATEXMKOPTS=-silent",
    ]
    sh(*cmd, *args)
