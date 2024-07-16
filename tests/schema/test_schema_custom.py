# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

from spin import backtick


def test_testplugin(cfg, tmpdir) -> None:
    """
    Using a test plugin named "testplugin" that uses lots of data types and
    interpolation to validate the enforcement of the schema.
    """
    output = backtick(
        f"spin -q -C tests/schema --env {tmpdir} -f test_schema.yaml "
        "--provision testplugin"
    )
    output = output.strip()
    print(output)
