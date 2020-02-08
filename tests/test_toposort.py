# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from pytest import raises

from spin.api import SpinError
from spin.cli import reverse_toposort


def test_valid():
    nodes = [1, 2, 3]
    graph = {1: [2], 2: [3]}
    assert reverse_toposort(nodes, graph) == [3, 2, 1]


def test_loop():
    nodes = [1, 2, 3]
    graph = {1: [2], 2: [3], 3: [1]}
    with raises(SpinError, match=".*cycle"):
        assert reverse_toposort(nodes, graph) == []
