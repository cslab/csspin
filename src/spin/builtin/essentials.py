# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

from spin import sh, task


@task("run", add_help_option=False)
def exec_shell(args):
    """Run a shell command in the project context."""
    if not args:
        args = ("{platform.shell}",)
    sh(*args)


def pretty_descriptor(prefix, name, descriptor):
    typename = " ".join(getattr(descriptor, "type", ["any"]))
    default = getattr(descriptor, "default", None)
    decl = f"{prefix}{name}: {typename}"
    if default:
        decl += f" = '{default}'"
    print(decl)
    helptext = getattr(descriptor, "help", "").split("\n")
    prefix = len(prefix) * " "
    for line in helptext:
        print(prefix + line)


@task()
def propinfo(cfg, args):
    schema = cfg.schema
    arg = "The Spinfile Schema"
    for arg in args:
        schema = schema.properties.get(arg)
    helptext = getattr(schema, "help", "--")
    pretty_descriptor("", arg, schema)
    properties = getattr(schema, "properties", {})
    for prop, desc in properties.items():
        pretty_descriptor("* ", prop, desc)
