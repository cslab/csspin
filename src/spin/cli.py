# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""spin is a simple task runner and sandbox provisioner that supports
re-usable task definitions. Task definitions are Python modules, that
are automatically provisioned.
"""

import os
import sys
from pprint import pprint
import importlib

import click
from .api import (
    config,
    Config,
    echo,
    cd,
    exists,
    mkdir,
    readyaml,
    merge_config,
    die,
    memoizer,
    sh,
    set_tree,
    get_tree,
    interpolate1,
)
from . import cruise


CRUISE_EXECUTOR_MAPPINGS = {
    "@docker": config(executor=cruise.DockerExecutor),
    "@host": config(executor=cruise.HostExecutor),
}


# These are the basic defaults for the top-level configuration
# tree. Sections and values will be added by loading plugins and
# reading the project configuration file (spinfile.yaml).
DEFAULTS = config(
    spin=config(
        spinfile="spinfile.yaml",
        spin_dir=".spin",
        spin_global="{spin.userprofile}/global.yaml",
        plugin_dir="{spin.spin_dir}/plugins",
        plugin_packages=[],
        userprofile="{HOME}/.spin",
    ),
    requirements=[],
    quiet=False,
    verbose=False,
    hooks=config(),
    cruise=Config(CRUISE_EXECUTOR_MAPPINGS),
)


def find_spinfile(spinfile):
    """Find a file 'spinfile' by walking up the directory tree."""
    cwd = os.getcwd()
    spinfile_ = spinfile
    while not os.path.exists(spinfile_):
        cwd_ = os.path.dirname(cwd)
        if cwd_ == cwd:
            break
        cwd = cwd_
        spinfile_ = os.path.join(cwd, spinfile)
    if os.path.exists(spinfile_):
        return os.path.abspath(spinfile_)
    die(f"{spinfile_} not found")


def load_plugin(cfg, import_spec, package=None):
    """Recursively load a plugin module.

    Load the plugin given by 'import_spec' and its dependencies
    specified in the module-level attribute 'requires' (list of
    absolute or relative import specs).
    """
    mod = importlib.import_module(import_spec, package)
    full_name = mod.__name__
    if full_name not in cfg.loaded:
        # This plugin module has not been imported so far --
        # initialize it and recursively load dependencies
        cfg.loaded[full_name] = mod
        settings_name = full_name.split(".")[-1]
        plugin_defaults = getattr(mod, "defaults", config())
        plugin_config_tree = cfg.setdefault(settings_name, config())
        mod.config = plugin_config_tree
        merge_config(plugin_config_tree, plugin_defaults)
        dependencies = [
            load_plugin(cfg, requirement, mod.__package__)
            for requirement in getattr(mod, "requires", [])
        ]
        mod.requires = [dep.__name__ for dep in dependencies]
    return mod


def reverse_toposort(nodes, graph):
    """Topologically sort nodes according to graph, which is a dict
    mapping nodes to dependencies.
    """
    graph = dict(graph)  # don't destroy the input
    counts = dict((n, 0) for n in nodes)
    for targets in graph.values():
        for n in targets:
            counts[n] += 1
    result = []
    independent = set(n for n in nodes if counts[n] == 0)
    while independent:
        n = independent.pop()
        result.insert(0, n)
        for m in graph.pop(n, ()):
            counts[m] -= 1
            if counts[m] == 0:
                independent.add(m)
    if graph:
        die("dependency graph has at least one cycle")

    return result


def toporun(cfg, *fn_names):
    """Run plugin functions named in 'fn_names' in topological order.

    """
    for func_name in fn_names:
        for pi_name in cfg.topo_plugins:
            pi_mod = cfg.loaded[pi_name]
            initf = getattr(pi_mod, func_name, None)
            if initf:
                initf(cfg)


# This is a click-style decorator that adds the basic command line
# options of spin to a click.command or click.group; we have this
# separately here, because we'll use it twice: a) for 'cli' below,
# which is our boostrap command, and b) for 'commands' which is the
# actual click group that collects sub commands from plugins. 'cli'
# uses these options to find the the configuration file, the project
# root and plugin directory, and then loads the plugins. 'commands'
# just has the same options, but doesn't use them except for
# generating the help text.
def base_options(fn):
    decorators = [
        click.option(
            "--change-directory",
            "-C",
            "cwd",
            type=click.Path(file_okay=False, exists=True),
            help="Change directory before doing anything else. "
            "In this case, the configuration file "
            "(spinfile.yaml) is expected to live in the "
            "directory changed to.",
        ),
        click.option(
            "-f",
            "spinfile",
            default=DEFAULTS.spin.spinfile,
            type=click.Path(dir_okay=False, exists=False),
            help="An alternative name for the configuration file. "
            "This can include a relative of absolute path when "
            "used without -C.",
        ),
        click.option(
            "--plugin-directory",
            "-P",
            "plugin_dir",
            type=click.Path(file_okay=False, exists=False),
            help="Alternative directory where spin installs and "
            "searches plugin packages. The default is "
            "{project_root}/.spin/plugins. This option overrides "
            "the 'spin.plugin_dir' setting.",
        ),
        click.option(
            "--quiet",
            "-q",
            is_flag=True,
            default=DEFAULTS.quiet,
            help="Be more quiet",
        ),
        click.option(
            "--verbose",
            "-v",
            is_flag=True,
            default=DEFAULTS.verbose,
            help="Be more verbose",
        ),
        click.option(
            "--debug",
            is_flag=True,
            default=False,
            help="Dump the configuration tree before processing.",
        ),
        click.option(
            "--cruise",
            "-c",
            multiple=True,
            help="Run spin in the given environment.",
        ),
        click.option(
            "-p",
            "properties",
            multiple=True,
            help="Set configuration property",
        ),
    ]
    for d in decorators:
        fn = d(fn)
    return fn


class GroupWithAliases(click.Group):
    def __init__(self, *args, **kwargs):
        click.Group.__init__(self, *args, **kwargs)
        self._aliases = {}

    def register_alias(self, alias, cmd_object):
        self._aliases[alias] = cmd_object

    def get_command(self, ctx, cmd_name):
        cmd = click.Group.get_command(self, ctx, cmd_name)
        if cmd is None:
            cmd = self._aliases.get(cmd_name, None)
        return cmd


@click.command(cls=GroupWithAliases, help=__doc__)
# Note that the base_options here are not actually used and ignore by
# 'commands'. Base options are processed by 'cli'.
@base_options
@click.pass_context
def commands(ctx, **kwargs):
    ctx.obj = get_tree()
    # FIXME: for commands like "cleanup" or "venv ..." it is idiotic
    # to run all initializations first. This should be supressable,
    # possibly by augmenting 'spin.plugin.task' or something ...
    toporun(ctx.obj, "configure", "init")


@commands.command()
@click.pass_context
def cleanup(ctx):
    """Call the 'cleanup' hook in all plugins.

    This is expected to eventually remove provisioned software
    (e.g. spin's Python interpreter, virtualenv etc.)
    """
    toporun(ctx.obj, "cleanup")


@click.command(
    context_settings=dict(
        allow_extra_args=True,
        ignore_unknown_options=True,
        # Override the default help option name -- we want click to
        # use the help of the main command group 'commands', not from
        # this boilerplate entry point.
        help_option_names=["--hidden-help-option"],
        auto_envvar_prefix="SPIN",
    )
)
@base_options
@click.pass_context
def cli(
    ctx, cwd, spinfile, plugin_dir, quiet, verbose, debug, cruise, properties
):
    # We want to honor the 'quiet' flag even if the configuration tree
    # has not yet been created.
    get_tree().quiet = quiet

    # Find a project file and load it.
    if cwd:
        cd(cwd)
    else:
        spinfile = find_spinfile(spinfile)

    cfg = set_tree(readyaml(spinfile))
    merge_config(cfg, DEFAULTS)

    # Merge user-specific globals if they exist
    if exists("{spin.spin_global}"):
        merge_config(cfg, readyaml(interpolate1("{spin.spin_global}")))

    # Reflect certain command line options in the config tree.
    cfg.quiet = quiet
    cfg.spin.spinfile = spinfile
    cfg.spin.project_root = "."

    # We have a proper config tree now in 'cfg'; cd to project root
    # and proceed.
    spinfile_dir = os.path.dirname(cfg.spin.spinfile)
    cd(spinfile_dir)

    # Setup plugin_dir, where spin installs plugin packages.
    if plugin_dir:
        cfg.spin.plugin_dir = plugin_dir
    if not os.path.isabs(cfg.spin.plugin_dir):
        cfg.spin.plugin_dir = os.path.abspath(
            os.path.join(spinfile_dir, cfg.spin.plugin_dir)
        )
    if not exists(cfg.spin.plugin_dir):
        mkdir(cfg.spin.plugin_dir)
    sys.path.insert(0, cfg.spin.plugin_dir)

    # Install plugin packages that are not yet installed, using pip
    # with the "-t" (target) option pointing to the plugin directory.
    with memoizer("{spin.spin_dir}/packages.memo") as m:
        for pkg in cfg.spin.plugin_packages:
            if not m.check(pkg):
                sh(
                    f"{sys.executable}",
                    "-m",
                    "pip",
                    "install",
                    "-t",
                    "{spin.plugin_dir}",
                    f"{pkg}",
                )
                m.add(pkg)

    # Load plugins. "Plugins" are not plugin packages, but modules
    # which we expect to live in plugin packages. Afterwards
    # 'cfg.loaded' will be a mapping from plugin names to module
    # objects.
    cfg.loaded = config()
    for import_spec in cfg.plugins:
        load_plugin(cfg, import_spec)

    # Create a topologically sorted list of the plugins by their
    # 'requires' dependencies. This will be used later by 'toporun' to
    # run initialization functions in order (e.g. a tool like 'flake8'
    # requires a virtualenv where it can be installed; the virtualenv
    # is provided by the 'virtualenv' plugin, which in turn requires
    # 'python', which provides a Python installation).
    nodes = cfg.loaded.keys()
    graph = dict(
        (n, getattr(mod, "requires", [])) for n, mod in cfg.loaded.items()
    )
    cfg.topo_plugins = reverse_toposort(nodes, graph)

    # Add command line settings.
    for prop in properties:
        k, v = prop.split("=")
        path = list(k.split("."))
        scope = cfg
        while len(path) > 1:
            scope = getattr(scope, path.pop(0))
        setattr(scope, path[0], v)

    build_cruises(cfg)

    # Debug aid: dump config tree for --debug
    if debug:
        echo("Configuration tree (debug):")
        pprint(cfg)

    if not cruise:
        # Invoke the main command group, which by now has all the
        # sub-commands from the plugins.
        commands.main(args=ctx.args)
    else:
        this_command = ["spin"]
        i = 1
        spinargs = True
        while i < len(sys.argv):
            if spinargs and sys.argv[i] in ("-c", "--cruise"):
                i += 1
            else:
                this_command.append(sys.argv[i])
            if not sys.argv[i].startswith("-"):
                spinargs = False
            i += 1
        for name, definition in match_cruises(cfg, cruise):
            executor = definition.executor(name, definition)
            executor.run(this_command)


def match_cruises(cfg, selectors):
    for name, definition in cfg.cruise.items():
        if name.startswith("@"):
            continue
        elif "@all" in selectors:
            yield name, definition
        if name in selectors:
            yield name, definition
        elif any(
            ("@" + tag in selectors) for tag in getattr(definition, "tags", [])
        ):
            yield name, definition


def build_cruises(cfg):
    for key in cfg.cruise.keys():
        if not key.startswith("@"):
            cruise = cfg.cruise[key]
            cruise.tags = cruise.tags.split()
            for tag in ["@" + tag for tag in cruise.tags]:
                if tag in cfg.cruise:
                    merge_config(cruise, cfg.cruise[tag])


def main():
    cli(auto_envvar_prefix="SPIN")
