# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/from spin import tree

from spin import tree


class TestYaml:
    def setup_method(self):
        self.config = tree.tree_load("tests/test_yaml.yaml")

    def test_empty(self):
        cfg = self.config["test_empty"]
        assert cfg is None

    def test_if(self):
        cfg = self.config["test_if"]
        assert hasattr(cfg, "check_true")
        assert not hasattr(cfg, "check_false")
        assert cfg["list_with_item"] == ["item"]
        assert cfg["list_without_item"] is None

    def test_var(self):
        cfg = self.config["test_var"]
        assert not hasattr(cfg, "var test")
        assert cfg["key1"] == "1"
        assert cfg["key2"] == "321"
