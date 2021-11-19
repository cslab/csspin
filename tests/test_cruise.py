# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import cli, cruise


def test_cruise():
    # debugging
    import sys

    import spin

    print(sys.path)
    print(spin.__path__)
    print(spin.__package__)
    print(spin.__name__)
    # debugging
    cfg = cli.load_config_tree("spinfile.yaml")

    def match(*selectors):
        return [name for name, _ in cruise.match_cruises(cfg, *selectors)]

    assert "linux" in match("linux")
    assert "host" in match("@all")
    assert "host" not in match("@docker")
