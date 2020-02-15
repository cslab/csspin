# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import config, sh


def init(cfg):
    modified = []
    cpi = sh(
        "git", "status", "--porcelain=v1", capture_output=True, silent=True
    )
    for line in cpi.stdout.decode().splitlines():
        x, y = line[0], line[1]
        names = line[3:].split(" -> ")
        fname = names[-1]
        if x in "M?" or y in "M?":
            modified.append(fname)
    cfg.vcs = config(modified=modified)
    cpi = sh("git", "diff", capture_output=True, silent=True)
    cfg.vcs.unidiff = cpi.stdout
