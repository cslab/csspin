# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import os

from spin import config, sh


def init(cfg):
    if os.path.isdir(".svn"):
        import svn.local

        client = svn.local.LocalClient(".")
        changes = client.status()
        # this not working for the ci
        modified = [f.name for f in changes if f.type in (1, 9)]
        cfg.vcs = config(modified=cfg.vcs.get("modified", []) + modified)
        cpi = sh("svn", "diff", capture_output=True, silent=True)
        cfg.vcs.unidiff = cpi.stdout
    elif os.path.isdir(".git"):
        from git import Repo

        repo = Repo(".")
        # this not working for the ci
        modified = [item.a_path for item in repo.index.diff(None)]
        cfg.vcs = config(modified=cfg.vcs.get("modified", []) + modified)
        cpi = sh("git", "diff", capture_output=True, silent=True)
        cfg.vcs.unidiff = cpi.stdout
