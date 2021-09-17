# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""Plugins that come with spin. These don't have to be installed
through a plugin package and are always available.
"""

import sys

import click
import distro
import entrypoints

from spin import (
    EXPORTS,
    argument,
    die,
    group,
    interpolate1,
    memoizer,
    option,
    parse_version,
    run_script,
    run_spin,
    sh,
    task,
    warn,
)


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
        if hasattr(descriptor, "noindex"):
            decl += "   :noindex:\n"
        helptext = getattr(descriptor, "help", "")
        decl += f"\n{helptext}\n"
    else:
        decl = "================\nSchema Reference\n================\n\n"
    return decl


@task()
def schemadoc(
    cfg,
    outfile: option("-o", "outfile", default="-", type=click.File("w")),  # noqa
    args,
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


@task()
def env(cfg):
    """Generate commands to activate an environment"""
    # FIXME: this is much better than patching virtualenv's activation
    # scripts -- and also more appropriate for other stacks. It does
    # not provide an easy way to "deactivate", though. We'd need that
    # for all kinds of shells, though.
    for name, value in EXPORTS.items():
        print(f"export {name}={value}")
    print(interpolate1(". {virtualenv.scriptdir}/activate"))


@group("global", noenv=True)
def globalgroup(ctx):
    """Subcommands for managing globally available plugins."""
    pass


@globalgroup.task("add")
def global_add(packages: argument(nargs=-1)):
    cmd = [
        f"{sys.executable}",
        "-m",
        "pip",
        "install",
        # "-q",
        "-t",
        "{spin.plugin_dir}",
    ]
    with memoizer("{spin.spin_global_plugins}/packages.memo") as m:
        for pkg in packages:
            sh(*cmd, f"{pkg}")
            if not m.check(pkg):
                m.add(pkg)


@globalgroup.task("ls")
def global_ls():
    for ep in entrypoints.get_group_all("spin.plugin"):
        print(ep.__dict__)


@globalgroup.task("rm")
def global_rm():
    pass


class TaskDefinition:
    def __init__(self, definition):
        self._definition = definition

    def __call__(self):
        env = self._definition.get("env", None)
        run_script(self._definition.get("script", []), env)
        run_spin(self._definition.get("spin", []))


def configure(cfg):
    """Grab explicitly defined tasks from the configuration tree and add
    them as subcommands.

    """
    for task_name, task_definition in cfg.get("extra-tasks", {}).items():
        help = task_definition.get("help", "")
        task(task_name, help=help)(TaskDefinition(task_definition))


def merge_dicts(a, b):
    for k, v in b.items():
        if k in a:
            a[k] = " ".join((a[k], v))
        else:
            a[k] = v


@task("system-provision", noenv=True)
def do_system_provisioning(
    cfg,
    distroargs: argument(nargs=-1),
):
    """Provision system dependencies for the host.

    This will output a script on stdout, that uses OS package managers
    like apt, yum etc. to install system-level dependencies for the
    project. The output can for example be piped into a sudo
    shell. This flag can not be combined with --cleanup, --provision
    or any subcommands.

    """
    if distroargs:
        distroname = distroargs[0]
        if len(distroargs) > 1:
            distroversion = parse_version(distroargs[1])
        else:
            distroversion = parse_version("")
    else:
        dinfo = distro.info()
        distroname = dinfo["id"]
        distroversion = parse_version(dinfo["version"])

    out = {}
    for pi in cfg.topo_plugins:
        supported = True
        fn = getattr(cfg.loaded[pi], "system_requirements", None)
        if fn is not None:
            supported = False
            reqs = fn(cfg)
            for check, items in reqs:
                if check(distroname, distroversion):
                    supported = True
                    merge_dicts(out, items)
        if not supported:
            warn(f"{pi} does not support {distroname} {distroversion}")

    supported = True
    system_requirements = cfg.get("system-requirements", None)
    if system_requirements:
        supported = False
        for check, items in system_requirements.items():
            check = eval(f"lambda distro, version: {check}")
            if check(distroname, distroversion):
                supported = True
                merge_dicts(out, items)
    if not supported:
        die(f"this project does not support {distroname} {distroversion}")

    for syscmd in ("apt-get", "yum", "dnf"):
        package_list = out.get(syscmd, "")
        if package_list:
            if syscmd == "apt-get":
                print("apt-get update")
            print(f"{syscmd} install -y {package_list}")
