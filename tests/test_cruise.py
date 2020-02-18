# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import cli, cruise


def test_cruise():
    cfg = cli.load_spinfile("spinfile.yaml")

    def match(*selectors):
        return [name for name, _ in cruise.match_cruises(cfg, *selectors)]

    assert "cp38-win" in match("cp38-win")
    assert "host" in match("@all")
    assert "host" not in match("@docker")
