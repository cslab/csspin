# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

from spin import config, sh


def init(cfg):
    from git import Repo

    repo = Repo(cfg.spin.project_root)
    modified = [item.a_path for item in repo.index.diff(None)]
    cfg.vcs = config(modified=modified)
    cpi = sh("git", "diff", capture_output=True, silent=True)
    cfg.vcs.unidiff = cpi.stdout
