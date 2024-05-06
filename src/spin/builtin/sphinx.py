# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

from spin import config, exists, rmtree, sh, task

defaults = config(
    docs="{spin.project_root}/docs",
    packages=[
        "sphinx",
    ],
    opts="-qaE",
    build_dir="{spin.project_root}/docs/_build",
)


def cleanup(cfg):
    if exists("{sphinx.build_dir}"):
        rmtree("{sphinx.build_dir}")


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
