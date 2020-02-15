import inspect

from pytest import raises

from spin import tree


def test_basic_dict():
    d1 = {1: 1, 2: 2}
    config = tree.ConfigTree(d1)
    assert d1 == config
    assert config[1] == 1
    with raises(KeyError):
        assert config[3] == 3

    foo = config.setdefault("foo", None)
    assert "foo" in config
    assert foo is None


def test_nested_bunch():
    config = tree.ConfigTree(subtree=tree.ConfigTree(foo="bar"))
    assert config.subtree.foo == "bar"
    assert tree.tree_keyname(config.subtree, "foo") == "subtree.foo"
    lines = tree.tree_dump(config).splitlines()
    assert lines[0].endswith("subtree:")
    assert lines[1].endswith("  foo: 'bar'")


def test_keyinfo_callsite():
    config = tree.ConfigTree(foo=None)
    config.foo = "foo"
    lno_foo_assign = inspect.currentframe().f_lineno - 1
    assert config.foo == "foo"

    ki = tree.tree_keyinfo(config, "foo")
    assert ki.file.endswith("test_tree.py")
    assert ki.line == lno_foo_assign

    tree.tree_update_key(config, "foo", "bar")
    assert ki.line == lno_foo_assign


def test_keyinfo_yamlfile():
    config = tree.tree_load("tests/sample.yaml")
    ki = tree.tree_keyinfo(config, "foo")
    assert ki.file.endswith("sample.yaml")
    assert ki.line == 1
