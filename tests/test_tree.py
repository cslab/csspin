# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/
#
# Disabling the protected-access rule since we are calling those on purpose.
# pylint: disable=protected-access

"""Module implementing the configuration tree related unit tests."""

import os
from inspect import currentframe
from os import environ

from click.exceptions import Abort
from pytest import raises

from spin import tree


def test_tree_typecheck() -> None:
    config = tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))
    result1 = tree.tree_typecheck(config, "sub", tree.ConfigTree(foo="bar"))
    assert result1 == tree.ConfigTree(foo="bar")

    result2 = tree.tree_typecheck(config, "sub", "baz")
    assert result2 == "baz"


def test_tree_update_key() -> None:
    """Checks if the tree_update_key function is able to update config trees."""
    config = tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))

    tree.tree_update_key(config, "sub", "strat")
    expected_config1 = tree.ConfigTree(sub="strat")
    assert config == expected_config1

    tree.tree_update_key(config, "key", "value")
    expected_config2 = tree.ConfigTree(sub="strat", key="value")
    assert config == expected_config2


def test__call_location() -> None:
    result = tree._call_location(depth=1)
    assert isinstance(result, tree.KeyInfo)
    assert isinstance(result.file, str)
    assert isinstance(result.line, int)
    assert result.file.endswith("test_tree.py")


def test__set_callsite() -> None:
    """
    Test checking that the KeyInfo is updated in case _set_callsite is
    called.

    FIXME: This test may be changed, since calling _set_callsite sets the file
    and line always to the location where this function is executed in
    'spin.tree.py'.
    """

    config = tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))

    ki_before = config._ConfigTree__keyinfo.get("sub")
    assert isinstance(ki_before, tree.KeyInfo)
    assert ki_before.file.endswith(__file__)

    tree._set_callsite(tree=config, key="sub", depth=1, value="baz")
    assert config == tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))

    ki_after = config._ConfigTree__keyinfo.get("sub")
    assert isinstance(ki_after, tree.KeyInfo)
    assert ki_after.file.endswith("tree.py")


def test_set_keyinfo() -> None:
    """
    Check updating key info to ensure that file and line are updated, but
    only if the key is present in the configuration tree.
    """
    config = tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))
    ki = config._ConfigTree__keyinfo["sub"]
    lineno = ki.line
    assert ki.file.endswith(__file__)

    # Check updating the KeyInfo
    assert (
        tree.tree_set_keyinfo(
            config,
            key="sub",
            ki=tree._call_location(1),
        )
        is None
    )
    assert "sub" in config._ConfigTree__keyinfo
    ki = config._ConfigTree__keyinfo["sub"]
    assert isinstance(ki, tree.KeyInfo)
    assert ki.file.endswith(__file__)
    assert ki.line > lineno

    # Setting key that is not in tree
    assert (
        tree.tree_set_keyinfo(
            config,
            key="sub2",
            ki=tree._call_location(1),
        )
        is None
    )
    assert "sub2" not in config


def test_tree_keyinfo() -> None:
    """Trivial test to retrieve the KeyInfo"""
    config = tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))
    assert tree.tree_keyinfo(config, "sub") == config._ConfigTree__keyinfo["sub"]
    with raises(Abort, match="key='bar' not in configuration tree."):
        tree.tree_keyinfo(config, "bar")


def test_tree_set_parent() -> None:
    parent = tree.ConfigTree(dad=tree.ConfigTree(name="Hans"))
    child = tree.ConfigTree(son=tree.ConfigTree(name="Foo"))
    tree.tree_set_parent(child, parent, "family")

    assert isinstance(child._ConfigTree__parentinfo, tree.ParentInfo)
    assert child._ConfigTree__parentinfo.parent == parent
    assert child._ConfigTree__parentinfo.key == "family"


def test_basic_dict() -> None:
    """Build a simple config tree and validate its properties."""
    d1 = {1: 1, 2: 2}
    config = tree.ConfigTree(d1)

    assert d1 == config
    assert config[1] == 1
    with raises(KeyError):
        assert config[3] == 3

    foo = config.setdefault("foo", None)  # pylint: disable=disallowed-name
    assert foo is None
    assert "foo" in config
    assert config["foo"] is None


def test_tree_keyname() -> None:
    """
    Tests creating a config tree while validating the correct assignment of
    subtrees as well as the expected return of the tree_dump.
    """
    config = tree.ConfigTree(
        subtree1=tree.ConfigTree(foo="bar"),
        subtree2=tree.ConfigTree(foo=["bar", "baz"]),
        subtree3=tree.ConfigTree(foo=[]),
        subtree4=tree.ConfigTree(foo={"bar": "baz"}),
        subtree5=tree.ConfigTree(foo={}),
    )
    assert config.subtree1.foo == "bar"
    assert config.subtree2.foo == ["bar", "baz"]
    assert config.subtree3.foo == []
    assert config.subtree4.foo == {"bar": "baz"}
    assert config.subtree5.foo == {}

    assert tree.tree_keyname(config.subtree1, "foo") == "subtree1.foo"
    assert tree.tree_keyname(config.subtree5, "foo") == "subtree5.foo"

    with raises(
        AttributeError,
        match="key='bar' not in tree=ConfigTree([('foo', 'bar')])",
    ):
        assert tree.tree_keyname(config.subtree1, "bar") == "subtree1.bar"

    lines = tree.tree_dump(config).splitlines()
    assert lines[0].endswith("subtree1:")
    assert lines[1].endswith("  foo: 'bar'")
    assert lines[2].endswith("subtree2:")
    assert lines[3].endswith("foo:")
    assert lines[4].endswith("- 'bar'")
    assert lines[5].endswith("- 'baz'")
    assert lines[6].endswith("subtree3:")
    assert lines[7].endswith("foo: []")
    assert lines[8].endswith("subtree4:")
    assert lines[9].endswith("foo:")  # FIXME: Shouldn't the dict values follow?
    assert lines[10].endswith("subtree5:")
    assert lines[11].endswith("foo: {}")

    # Don't forget to check the root
    assert tree.tree_keyname(config, "subtree1") == "subtree1"


def test_keyinfo_callsite() -> None:
    """Function validating the source of assignment of config tree elements."""
    config = tree.ConfigTree(foo=None)
    config.foo = "foo"
    lno_foo_assign = currentframe().f_lineno - 1  # type: ignore[union-attr]
    assert config.foo == "foo"

    ki = tree.tree_keyinfo(config, "foo")
    assert ki.file.endswith("test_tree.py")
    assert ki.line == lno_foo_assign

    tree.tree_update_key(config, "foo", "bar")
    assert ki.line == lno_foo_assign


def test_tree_load() -> None:
    """Function validating the source of assignment for a loaded config file."""
    config = tree.tree_load(os.path.join("tests", "sample.yaml"))
    ki = tree.tree_keyinfo(config, "foo")
    assert ki.file.endswith("sample.yaml")
    assert ki.line == 1


def test_update() -> None:
    """Validating the update/override of configuration tree values."""
    a = tree.ConfigTree(sub=tree.ConfigTree(a="a"))
    b = tree.ConfigTree(sub=tree.ConfigTree(a="b"))
    tree.tree_update(a, b)
    assert a.sub.a == "b"


def test_update_failing() -> None:
    """
    Ensures that updating the tree fails if the the type of source values don't
    match those of the target tree.
    """
    from spin import config, schema

    test_schema = schema.build_schema(
        config(
            sub=config(
                type="object",
                properties=config(a=config(type="list")),
            )
        )
    )
    a = test_schema.get_default()
    a.sub.a = ["a"]
    b = tree.ConfigTree(sub=tree.ConfigTree(a=1))

    with raises(
        Abort,
        match=(
            f".*:{tree.tree_keyinfo(b.sub, 'a').line}: cannot assign '1' to 'a': 'int'"
            " object is not iterable"
        ),
    ):
        tree.tree_update(a, b)


def test_merge() -> None:
    """Function validating the merge of configuration trees"""
    a = tree.ConfigTree(sub=tree.ConfigTree(a="a"))
    b = tree.ConfigTree(sub=tree.ConfigTree(a="a", b="b"))
    c = tree.ConfigTree(sub=tree.ConfigTree(a="b", b="c", c="c"))

    tree.tree_merge(a, b)
    tree.tree_merge(a, c)

    assert a.sub.a == "a"
    assert a.sub.b == "b"
    assert a.sub.c == "c"

    dummy = {"sub": {"a": "a"}}
    with raises(
        Abort,
        match="Can't merge tree's since 'source' is not type 'spin.tree.ConfigTree'",
    ):
        tree.tree_merge(a, dummy)

    with raises(
        Abort,
        match="Can't merge tree's since 'target' is not type 'spin.tree.ConfigTree'",
    ):
        tree.tree_merge(dummy, a)


def test_directive_append() -> None:
    """Validating the expected results of the directive_append function"""
    config = tree.ConfigTree(sub=tree.ConfigTree(foo=["bar"]))

    tree.directive_append(config["sub"], "foo", "baz")
    expected_config1 = tree.ConfigTree(sub=tree.ConfigTree(foo=["bar", "baz"]))
    assert config == expected_config1

    tree.directive_append(config["sub"], "foo", ["buz", "biz"])
    expected_config2 = tree.ConfigTree(
        sub=tree.ConfigTree(foo=["bar", "baz", "buz", "biz"])
    )
    assert config == expected_config2


def test_directive_append_failing() -> None:
    """
    Validating the expected results of the directive_append function when
    passing undesirable values.
    """
    config = tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))
    with raises(Abort, match=".*Can't append value='x' to tree since.*"):
        tree.directive_append(config, "sub", "x")

    with raises(Abort, match=".*key='a' not in passed target tree."):
        tree.directive_append(config, "a", "x")


def test_directive_prepend() -> None:
    """Validating the expected results of the directive_prepend function"""
    config = tree.ConfigTree(sub=tree.ConfigTree(foo=["bar"]))

    tree.directive_prepend(config["sub"], "foo", "baz")
    expected_config1 = tree.ConfigTree(sub=tree.ConfigTree(foo=["baz", "bar"]))
    assert config == expected_config1

    tree.directive_prepend(config["sub"], "foo", ["buz", "biz"])
    expected_config2 = tree.ConfigTree(
        sub=tree.ConfigTree(foo=["buz", "biz", "baz", "bar"])
    )
    assert config == expected_config2


def test_directive_prepend_failing() -> None:
    """
    Validating the expected results of the directive_prepend function when
    passing undesirable values.
    """
    config = tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))
    with raises(Abort, match=".*Can't prepend value='x' to tree since.*"):
        tree.directive_prepend(config, "sub", "x")

    with raises(Abort, match=".*key='a' not in passed target tree."):
        tree.directive_prepend(config, "a", "x")


def test_directive_interpolate() -> None:
    """
    Checks the effectiveness for the directive_interpolation function which
    makes use of the interpolate1 function.
    """
    config = tree.ConfigTree(sub=tree.ConfigTree(foo="bar"))

    tree.directive_interpolate(config, "sub", "tree")
    expected_config1 = tree.ConfigTree(sub="tree")
    assert config == expected_config1

    tree.directive_interpolate(config, "cache", "'{SPIN_CACHE}'")
    expected_config2 = tree.ConfigTree(sub="tree", cache=f"'{environ['SPIN_CACHE']}'")
    assert config == expected_config2
