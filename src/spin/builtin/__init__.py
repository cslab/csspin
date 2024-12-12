# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""Plugins that come with spin. These don't have to be installed
through a plugin package and are always available.
"""

import sys

import click
import distro

from spin import (
    argument,
    confirm,
    die,
    option,
    parse_version,
    rmtree,
    run_script,
    run_spin,
    sh,
    task,
    toporun,
    warn,
)
from spin.cli import (
    commands,
    finalize_cfg_tree,
    install_plugin_packages,
    load_plugins_into_tree,
)


@task("run", add_help_option=False)
def exec_shell(ctx, args):
    """Run a shell command in the project context."""
    if not args:
        die("Use of run is not possible without arguments.")
    if "--help" == args[0]:
        subcommand_obj = commands.get_command(ctx, "run")
        click.echo(subcommand_obj.get_help(ctx))
    else:
        sh(*args)


def pretty_descriptor(parent, name, descriptor, rst: bool):
    types = getattr(descriptor, "type", ["any"])
    default = getattr(descriptor, "default", None)
    if name:
        if parent:
            name = f"{parent}.{name}"
        if rst:
            joined_types = " ".join(types)
            decl = f".. py:data:: {name}\n   :type: '{joined_types}'\n"
            if default:
                decl += f"   :value: '{default}'\n"
            if hasattr(descriptor, "noindex") or "object" in types:
                decl += "   :noindex:\n"
        else:
            joined_types = ", ".join(types)
            decl = f"{name}: [{joined_types}]"
            if default:
                decl += f" = '{default}'"
        helptext = getattr(descriptor, "help", "")
        if not helptext.endswith("\n"):
            helptext += "\n"
        decl += f"\n{helptext}\n"
    else:
        decl = "================\nSchema Reference\n================\n\n"
    return decl


@task()
def schemadoc(
    cfg,
    outfile: option(
        "-o",
        "outfile",
        default="-",  # noqa: F722
        type=click.File("w"),
        help="Write output into FILENAME.",  # noqa: F722
    ),
    full: option(
        "--full",
        default=True,
        type=click.BOOL,
        help="Show schema documentation for the whole ConfigTree.",  # noqa: F722
    ),
    rst: option(
        "--rst",
        is_flag=True,
        default=False,
        type=click.BOOL,
        help="Print the schema documentation in rst format.",  # noqa: F722
    ),
    select: argument(
        type=click.STRING,
        default="",  # noqa: F722
        callback=lambda ctx, param, value: value.split(".") if value else "",
    ),
):
    """Print the schema definitions for cs.spin."""

    def do_docwrite(parent, name, desc, ignore=tuple()):
        fullname = f"{parent}.{name}" if parent else name
        if fullname in ignore:
            return

        outfile.write(pretty_descriptor(parent, name, desc, rst))
        properties = getattr(desc, "properties", {})
        for prop, descr in properties.items():
            do_docwrite(fullname, prop, descr, ignore)

    schema = cfg.schema

    ignore = []
    if not full:
        for import_spec in cfg.loaded:
            if "spin." in import_spec:
                continue
            import_spec = tuple(import_spec.split("."))
            plugin_name = import_spec[-1]
            ignore.append(plugin_name)

    arg = ""
    for arg in select:
        schema = schema.properties.get(arg)
    parent = "" if len(select) < 2 else ".".join(select[:-1])
    do_docwrite(parent, arg, schema, ignore)


class TaskDefinition:
    def __init__(self, definition):
        self._definition = definition

    def __call__(self):
        env = self._definition.get("env", None)
        run_spin(self._definition.get("spin", []))
        run_script(self._definition.get("script", []), env)


def configure(cfg):
    """Grab explicitly defined tasks from the configuration tree and add
    them as subcommands.

    """
    for clause_name in ("extra_tasks", "tasks"):
        for task_name, task_definition in cfg.get(clause_name, {}).items():
            task(task_name, help=task_definition.get("help", ""))(
                TaskDefinition(task_definition)
            )


def merge_dicts(a, b):
    for k, v in b.items():
        if k in a:
            # We support lists and strings in system_requirements;
            # this is not very robust, though.
            if isinstance(v, list):
                a[k].extend(v)
            else:
                a[k] = " ".join((a[k], v))
        else:
            a[k] = v


def get_distro():
    dinfo = distro.info()
    if sys.platform == "win32":
        dinfo["id"] = "windows"
        winver = sys.getwindowsversion()
        dinfo["version"] = f"{winver.major}.{winver.minor}.{winver.build}"
    return dinfo


@task("system-provision", noenv=True)
def do_system_provisioning(
    cfg,
    distroargs: argument(nargs=-1),
):
    """Provision system dependencies for the host.

    Usage:
        spin system-provision [<distro> [<version>]]

    This will output a script on stdout, that uses OS package managers like apt,
    yum etc. to install system-level dependencies for the project. The output
    can for example be piped into a sudo shell.
    """
    # Install the plugins and build the full config tree
    install_plugin_packages(cfg)
    load_plugins_into_tree(cfg)
    finalize_cfg_tree(cfg)

    if distroargs:
        distroname = distroargs[0]
    else:
        dinfo = get_distro()
        distroname = dinfo["id"]

    # Check system requirements of individual plugins
    out = {}
    supported = True
    for pi in cfg.spin.topo_plugins:
        defaults = cfg.loaded[pi].defaults
        if defaults.get("requires") and defaults.requires.get("system"):
            system_requirements = defaults.requires.system
            if distroname not in system_requirements.keys():
                warn(
                    f"The '{pi}' plugin does not officially support"
                    f" {distroname}. You can see which packages to"
                    " manually install by running 'spin system-provision debian'"
                )
                supported = False
            else:
                merge_dicts(out, system_requirements.get(distroname, []))

    # Check system requirements defined within the configuration tree, usually
    # defined the projects' spinfile.yaml.
    if cfg.system_requirements.keys():
        if distroname not in cfg.system_requirements.keys():
            warn(
                "This project does not officially support"
                f" {distroname}. You can see which packages to manually"
                " install by running 'spin system-provision debian'"
            )
            supported = False
        else:
            merge_dicts(out, cfg.system_requirements.get(distroname, []))

    for line in out.get("before", []):
        print(line)

    for syscmd in ("apt", "choco"):
        if (package_list := out.get(syscmd, [])) and supported:
            print(f"{syscmd} install -y {' '.join(package_list)}")

    for line in out.get("after", []):
        print(line)


@task("distro", noenv=True)
def distro_task(cfg):
    """Print the distro information."""
    dinfo = get_distro()
    print(f"distro={repr(dinfo['id'])} version={parse_version(dinfo['version'])}")


@task("provision", noenv=True)
def provision(cfg):
    """
    Create or update a development environment.
    """
    # Install the plugins and build the full config tree
    install_plugin_packages(cfg)
    load_plugins_into_tree(cfg)
    finalize_cfg_tree(cfg)

    toporun(cfg, "provision")
    toporun(cfg, "finalize_provision")


@task(noenv=True)
def cleanup(
    cfg,
    purge: option(
        "--purge",
        is_flag=True,
        help="Removes spin plugin data.",  # noqa: F722
    ),
    skip_confirmation: option(
        "-y",
        "--yes",
        "skip_confirmation",
        is_flag=True,
        help="Skip confirmation when using --purge.",  # noqa: F722
    ),
):
    """
    Clean up project-local resources that have been provisioned by spin, e.g.
    virtual environments and {project_root}/.spin. Also deletes {spin.data}
    if --purge is passed.
    """
    if (
        purge
        and not skip_confirmation
        and not (
            confirm(
                f"You are about to delete all plugin's data in {cfg.spin.data}."
                " Continue?"
            )
        )
    ):
        return

    # Load the plugins as far as they are available.
    load_plugins_into_tree(cfg, cleanup=True)

    # Do not configure and sanitize in case of cleanup, since plugin
    # packages may not be installed, causing AttributeErrors in case of
    # accessing not-initialized plugins via "cfg." as well as failures due
    # to interpolation against property tree keys that does not exist.

    toporun(cfg, "cleanup", reverse=True)
    rmtree(cfg.spin.spin_dir / "plugins")

    if purge:
        rmtree(cfg.spin.data)
