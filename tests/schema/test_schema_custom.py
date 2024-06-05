# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

from spin import backtick, cli


def test_testplugin(tmpdir) -> None:
    """
    Using a test plugin named "testplugin" that uses lots of data types and
    interpolation to validate the enforcement of the schema.
    """
    cli.load_config_tree(None)
    output = backtick(
        f"spin -q -C tests/schema --env {tmpdir} -f test_schema.yaml "
        "--provision testplugin"
    )
    output = output.strip()
    print(output)
