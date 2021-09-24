# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from click.testing import CliRunner

from spin import cd, cli, mkdir, writetext


def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["--help"])
    assert result.exit_code == 0


def test_find_spinfile(tmpdir):
    spinf = os.path.normpath(f"{tmpdir}/xx.yaml")
    writetext(spinf, "")
    insidetree = f"{tmpdir}/a/b/c"
    mkdir(insidetree)
    with cd(insidetree):
        location1 = cli.find_spinfile("xx.yaml")
        location2 = cli.find_spinfile("SPIN_TEST_CLI_DOESNOTEXIST")
    assert location1 == spinf
    assert location2 is None
