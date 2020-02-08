# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from click.testing import CliRunner

from spin.cli import cli


def test_flake8():
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--debug", "flake8", "--exit-zero", "./tests"]
    )
    assert result.exit_code == 0
    assert result.output.startswith("spin")
