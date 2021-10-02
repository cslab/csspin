# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, group, interpolate1, sh

defaults = config(
    executable="docker",
    hub="",
    name="",
    tags=["latest"],
    build_options=[],
)


@group()
def docker(cfg):
    pass


@docker.task()
def build(cfg):
    options = []
    if "INSIDE_EMACS" in os.environ:
        options.append("--progress=plain")
    for definition in cfg.docker.images:
        build_args = []
        for key, value in definition.get("args", config()).items():
            build_args.extend(["--build-arg", interpolate1(f"{key}={value}")])
        sh(
            "{docker.executable}",
            "build",
            *cfg.docker.build_options,
            *options,
            *build_args,
            "-f",
            definition.dockerfile,
            "-t",
            definition.tag,
            ".",
        )

    # if cfg.docker.name:
    #     imagename = "/".join((cfg.docker.hub, cfg.docker.name))
    #     for tag in cfg.docker.tags:
    #         options.extend(["-t", f"{imagename}:{tag}"])
    # options.append(cfg.docker.dockerdir)
    # if cfg.docker.dockerfile:
    #     options.extend(["-f", cfg.docker.dockerfile])
    # sh("{docker.executable}", "build", *options)


@docker.task()
def push(cfg):
    for definition in cfg.docker.images:
        sh(
            "{docker.executable}",
            "push",
            cfg.quietflag,
            definition.tag,
        )
