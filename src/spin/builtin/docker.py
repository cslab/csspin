# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import config, interpolate1, sh

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
def docker():
    pass


@docker.task()
def build(cfg):
    if cfg.docker.name:
        imagename = "/".join(cfg.docker.hub, cfg.docker.name)
        tag_options = []
        for tag in cfg.docker.tags:
            tag_options.extend(["-t", f"{imagename}:{tag}"])
    build_options = [cfg.docker.dockerdir]
    if cfg.docker.dockerfile:
        build_options.extend(["-f", cfg.docker.dockerfile])
    sh("{docker.executable}", "build", *tag_options, *build_options)
