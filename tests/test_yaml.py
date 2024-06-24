# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

from __future__ import annotations

import os

from spin import tree


class TestYaml:
    def setup_method(self: TestYaml) -> None:
        self.config = tree.tree_load(
            os.path.join(
                "tests",
                "yamls",
                "test_yaml.yaml",
            )
        )

    def test_empty(self: TestYaml) -> None:
        cfg = self.config["test_empty"]
        assert cfg is None

    def test_if(self: TestYaml) -> None:
        cfg = self.config["test_if"]
        assert hasattr(cfg, "check_true")
        assert not hasattr(cfg, "check_false")
        assert cfg["list_with_item"] == ["item"]
        assert cfg["list_without_item"] is None

    def test_var(self: TestYaml) -> None:
        cfg = self.config["test_var"]
        assert not hasattr(cfg, "var test")
        assert cfg["key1"] == "1"
        assert cfg["key2"] == "321"
