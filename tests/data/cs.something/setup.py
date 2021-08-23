# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 1990 - 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

from cdb.comparch.pkgtools import setup

setup(
    name="cs.something",
    version="15.1.0",
    install_requires=["cs.platform", "cs.web"],
    docsets=[],
    cdb_modules=[],
    cdb_services=[],
)
