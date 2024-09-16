# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""Module implementing tests related to directive support"""

from path import Path


def test_directive_append(directive_spinfile: Path) -> None:
    """
    Ensuring that directive_append works for plugins without schemas and
    nested properties.
    """
    cfg = directive_spinfile
    assert cfg.directives.test_append.opts == ["a", "b", "c", "d"]
    assert not hasattr(cfg.directives.test_append, "append opts")
    assert cfg.directives.test_append.nested_append.opts == ["w", "x", "y", "z"]
    assert not hasattr(cfg.directives.test_append.nested_append, "append opts")


def test_directive_prepend(directive_spinfile: Path) -> None:
    """
    Ensuring that directive_prepend works for plugins without schemas and
    nested properties.
    """
    cfg = directive_spinfile
    assert cfg.directives.test_prepend.opts == ["d", "a", "b", "c"]
    assert not hasattr(cfg.directives.test_prepend, "prepend opts")
    assert cfg.directives.test_prepend.nested_prepend.opts == ["z", "w", "x", "y"]
    assert not hasattr(cfg.directives.test_prepend.nested_prepend, "prepend opts")


def test_directive_interpolate(directive_spinfile: Path) -> None:
    """
    Ensuring that directive_interpolate works for plugins without schemas and
    nested properties.
    """
    cfg = directive_spinfile
    assert cfg.directives.test_interpolate.opts == cfg.spin.cache
    assert not hasattr(cfg.directives.test_interpolate, "interpolate opts")
    assert cfg.directives.test_interpolate.nested_interpolate.opts == cfg.spin.cache
    assert not hasattr(
        cfg.directives.test_interpolate.nested_interpolate, "interpolate opts"
    )


def test_directives_without_default_defined_in_spinfile(
    directive_spinfile: Path,
) -> None:
    """
    Ensuring that directives works for plugins without schemas - with the
    special case that
    """

    cfg = directive_spinfile
    assert cfg.directives.test_setting_1 == ["b", "foo", "a"]
    assert not hasattr(cfg.directives, "append test_setting_1")
    assert cfg.directives.test_setting_2 == cfg.spin.cache
    assert not hasattr(cfg.directives, "append test_setting_2")
