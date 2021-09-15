# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import click

from spin import option, sh, task


@task("run", add_help_option=False)
def exec_shell(args):
    """Run a shell command in the project context."""
    if not args:
        args = ("{platform.shell}",)
    sh(*args)


def pretty_descriptor(parent, name, descriptor):
    typename = " ".join(getattr(descriptor, "type", ["any"]))
    default = getattr(descriptor, "default", None)
    if name:
        if parent:
            name = f"{parent}.{name}"
        decl = f".. py:data:: {name}\n   :type: '{typename}'\n"
        if default:
            decl += f"   :value: '{default}'\n"
        helptext = getattr(descriptor, "help", "")
        decl += f"\n{helptext}\n"
    else:
        decl = "================\nSchema Reference\n================\n\n"
    return decl


@task()
def schemadoc(
    cfg, outfile: option("-o", "outfile", default="-", type=click.File("w")), args
):
    schema = cfg.schema
    arg = ""
    for arg in args:
        schema = schema.properties.get(arg)

    def do_docwrite(parent, name, desc):
        outfile.write(pretty_descriptor(parent, name, desc))
        properties = getattr(desc, "properties", {})
        for prop, desc in properties.items():
            do_docwrite(name, prop, desc)

    do_docwrite("", arg, schema)
