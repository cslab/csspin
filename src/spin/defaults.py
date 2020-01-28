# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from .util import config

DEFAULTS = config(
    spin=config(
        spinfile="spinfile.yaml",
        plugin_dir=".spin",
        plugin_packages=[],
        userprofile="{HOME}/.spin",
    ),
    requirements=[],
    quiet=False,
)
