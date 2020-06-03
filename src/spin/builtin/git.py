# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from git import Repo

from spin import config, sh


def init(cfg):
    repo = Repo(".")
    modified = [item.a_path for item in repo.index.diff(None)]
    cfg.vcs = config(modified=modified)
    cpi = sh("git", "diff", capture_output=True, silent=True)
    cfg.vcs.unidiff = cpi.stdout
