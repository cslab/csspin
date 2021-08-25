# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

import svn.local
from git import Repo

from spin import config, sh


def init(cfg):
    if os.path.isdir(".svn"):
        client = svn.local.LocalClient(".")
        changes = client.status()
        modified = [f.name for f in changes if f.type in (1, 9)]
        cfg.vcs = config(modified=modified)
        cpi = sh("svn", "diff", capture_output=True, silent=True)
        cfg.vcs.unidiff = cpi.stdout
    elif os.path.isdir(".git"):
        repo = Repo(".")
        modified = [item.a_path for item in repo.index.diff(None)]
        cfg.vcs = config(modified=modified)
        cpi = sh("git", "diff", capture_output=True, silent=True)
        cfg.vcs.unidiff = cpi.stdout
