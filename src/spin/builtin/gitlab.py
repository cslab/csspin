# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import config, download, exists, normpath, sh, task

defaults = config(
    runner_url="https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64",
    cmd="{spin.cache}/{platform.tag}/gitlab-runner",
    exec_options=[],
)


def ensure_gitlab_runner(cfg):
    if not exists(cfg.gitlab.cmd):
        download(cfg.gitlab.runner_url, cfg.gitlab.cmd)
        sh("chmod", "+x", cfg.gitlab.cmd)


@task(add_help_option=False)
def gitlab(cfg, args):
    ensure_gitlab_runner(cfg)
    sh(cfg.gitlab.cmd, *args)
