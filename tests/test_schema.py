# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from pytest import raises

from spin import config, schema


def test_simple():
    sch = schema.build_schema(
        config(
            x=config(type="list"),
            subtree=config(
                type="object", properties=config(a=config(type="path"))
            ),
        )
    )
    i = sch.get_default()
    assert i._ConfigTree__schema is sch
    assert i.subtree._ConfigTree__schema is sch.properties["subtree"]
    i.x = "a b c"
    assert i.x == ["a", "b", "c"]
    with raises(TypeError):
        i.x = 12
    assert i.x == ["a", "b", "c"]

    i.subtree.a = "file"
    assert repr(i.subtree.a) == "Path('file')"

    with raises(schema.SchemaError):
        i.subtree = "das geht nicht"
