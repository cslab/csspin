# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import config, download, exists, normpath, sh, task

defaults = config(
    cmd="gitlab-ci-local",
    requires=config(
        npm=["gitlab-ci-local"],
    ),
)


@task("gitlab-ci", add_help_option=False)
def gitlab(cfg, args):
    sh(cfg.gitlab.cmd, *args)
