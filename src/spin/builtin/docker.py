# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, group, sh

defaults = config(
    executable="docker",
    hub="",
    name="",
    tags=["latest"],
    build_args=[],
    dockerfile=None,
    dockerdir=".",
)


@group()
def docker(cfg):
    pass


@docker.task()
def build(cfg):
    options = []
    if not cfg.verbose:
        options.append("-q")
    if "INSIDE_EMACS" in os.environ:
        options.append("--progress=plain")
    if cfg.docker.name:
        imagename = "/".join((cfg.docker.hub, cfg.docker.name))
        for tag in cfg.docker.tags:
            options.extend(["-t", f"{imagename}:{tag}"])
    options.append(cfg.docker.dockerdir)
    if cfg.docker.dockerfile:
        options.extend(["-f", cfg.docker.dockerfile])
    sh("{docker.executable}", "build", *options)


@docker.task()
def push(cfg):
    options = []
    if not cfg.verbose:
        options.append("-q")
    if cfg.docker.name:
        imagename = "/".join((cfg.docker.hub, cfg.docker.name))
        for tag in cfg.docker.tags:
            sh("{docker.executable}", "push", *options, f"{imagename}:{tag}")
