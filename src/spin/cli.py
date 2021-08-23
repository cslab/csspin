# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""spin is a task runner with a twist.

It supports reusable task definitions in the form of Python modules,
that are automatically provisioned.

"""

import importlib
import os
import sys

import click

import entrypoints

from . import (
    cd,
    config,
    cruise,
    die,
    exists,
    get_tree,
    interpolate1,
    memoizer,
    mkdir,
    readyaml,
    schema,
    set_tree,
    sh,
    toporun,
    tree,
)


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
        userprofile=os.path.expanduser("~/.spin"),
        extra_index="https://packages.contact.de/apps/x.x",
    ),
    quiet=False,
    verbose=False,
    cruise=config(CRUISE_EXECUTOR_MAPPINGS),
    platform=config(
        exe=".exe" if sys.platform == "win32" else "", shell="{SHELL}"
    ),
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
    return None


def load_plugin(cfg, import_spec, package=None):
    """Recursively load a plugin module.

    Load the plugin given by 'import_spec' and its dependencies
    specified in the module-level configuration key 'requires' (list
    of absolute or relative import specs).

    """
    try:
        mod = importlib.import_module(import_spec, package)
    except ModuleNotFoundError:
        die(f"failed to load plugin '{import_spec}'")
    full_name = mod.__name__
    if full_name not in cfg.loaded:
        # This plugin module has not been imported so far --
        # initialize it and recursively load dependencies
        cfg.loaded[full_name] = mod
        settings_name = full_name.split(".")[-1]
        plugin_defaults = getattr(mod, "defaults", config())
        plugin_config_tree = cfg.setdefault(settings_name, config())
        if plugin_defaults:
            tree.tree_set_keyinfo(
                cfg,
                settings_name,
                tree.tree_keyinfo(
                    plugin_defaults, list(plugin_defaults.keys())[0]
                ),
            )
        tree.tree_merge(plugin_config_tree, plugin_defaults)
        dependencies = [
            load_plugin(cfg, requirement, mod.__package__)
            for requirement in plugin_config_tree.get("requires", [])
        ]
        ki = None
        if "requires" in plugin_config_tree:
            ki = tree.tree_keyinfo(plugin_config_tree, "requires")
        plugin_config_tree.requires = [dep.__name__ for dep in dependencies]
        if ki:
            tree.tree_set_keyinfo(plugin_config_tree, "requires", ki)
        mod.defaults = plugin_config_tree
    return mod


def reverse_toposort(nodes, graph):
    """Topologically sort nodes according to graph, which is a dict
    mapping nodes to dependencies.
    """
    graph = dict(graph)  # don't destroy the input
    counts = {n: 0 for n in nodes}
    for targets in graph.values():
        for n in targets:
            counts[n] += 1
    result = []
    independent = {n for n in nodes if counts[n] == 0}
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


# This is a click-style decorator that adds the basic command line
# options of spin to a click.command or click.group; we have this
# separately here, because we'll use it twice: a) for 'cli' below,
# which is our bootstrap command, and b) for 'commands' which is the
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
            "This can include a relative or absolute path when "
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
            "cruiseopt",
            multiple=True,
            help="Run spin in the given environment.",
        ),
        click.option(
            "--interactive",
            "-i",
            is_flag=True,
            default=False,
            help="Run docker commands using -it.",
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
    # For commands like "cleanup" or "venv ..." it is idiotic to run
    # all initializations first. This should be supressable, possibly
    # by augmenting 'spin.plugin.task' or something ...
    toporun(ctx.obj, "init")


@click.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        # Override the default help option name -- we want click to
        # use the help of the main command group 'commands', not from
        # this boilerplate entry point.
        "help_option_names": ["--hidden-help-option"],
        "auto_envvar_prefix": "SPIN",
        "allow_interspersed_args": False,
    }
)
@base_options
@click.pass_context
def cli(
    ctx,
    cwd,
    spinfile,
    plugin_dir,
    quiet,
    verbose,
    debug,
    cruiseopt,
    interactive,
    properties,
):
    # We want to honor the 'quiet' flag even if the configuration tree
    # has not yet been created.
    get_tree().quiet = quiet

    # Find a project file and load it.
    if cwd:
        cd(cwd)
    else:
        spinfile = find_spinfile(spinfile)

    cfg = load_spinfile(spinfile, cwd, quiet, verbose, plugin_dir, properties)

    # Debug aid: dump config tree for --debug
    if debug:
        print(tree.tree_dump(cfg))

    if not cruiseopt:
        # Invoke the main command group, which by now has all the
        # sub-commands from the plugins.
        kwargs = getattr(cli, "click_main_kwargs", {})
        commands.main(args=ctx.args, **kwargs)
    else:
        cruise.do_cruise(cfg, cruiseopt, interactive)


def find_plugin_packages(cfg):
    # Packages that are required to load plugins are identified by
    # the keys in dict-valued list items of the 'plugins' setting
    for item in cfg.get("plugins", []):
        if isinstance(item, dict):
            for key in item.keys():
                yield key


def yield_plugin_import_specs(cfg):
    for item in cfg.get("plugins", []):
        if isinstance(item, dict):
            for package_value in item.values():
                if isinstance(package_value, list):
                    for import_spec in package_value:
                        yield import_spec
                else:
                    yield package_value
        else:
            yield f"spin.builtin.{item}"


def load_spinfile(
    spinfile,
    cwd=False,
    quiet=False,
    verbose=False,
    plugin_dir=None,
    properties=(),
):
    spinschema = schema.schema_load(
        os.path.join(os.path.dirname(__file__), "schema.yaml")
    )
    cfg = spinschema.get_default()
    set_tree(cfg)
    userdata = readyaml(spinfile) if spinfile else config()
    tree.tree_update(cfg, userdata)
    tree.tree_merge(cfg, DEFAULTS)

    # Merge user-specific globals if they exist
    if exists("{spin.spin_global}"):
        tree.tree_merge(cfg, readyaml(interpolate1("{spin.spin_global}")))

    # Reflect certain command line options in the config tree.
    cfg.quiet = quiet
    cfg.verbose = verbose
    cfg.spin.spinfile = spinfile
    cfg.spin.project_root = "."

    # We have a proper config tree now in 'cfg'; cd to project root
    # and proceed.
    if spinfile:
        spinfile_dir = os.path.dirname(os.path.abspath(cfg.spin.spinfile))
        cfg.spin.spinfile_dir = spinfile_dir
        if not cwd:
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
        sys.path.insert(0, interpolate1(cfg.spin.plugin_dir))

        cmd = [
            f"{sys.executable}",
            "-m",
            "pip",
            "install",
            "-q",
            "-t",
            "{spin.plugin_dir}",
        ]

        extra_index = cfg.spin.extra_index
        if extra_index:
            cmd.extend(["--extra-index-url", extra_index])

        # Install plugin packages that are not yet installed, using pip
        # with the "-t" (target) option pointing to the plugin directory.
        with memoizer("{spin.plugin_dir}/packages.memo") as m:
            replacements = cfg.get("devpackages", {})
            for pkg in find_plugin_packages(cfg):
                pkg = replacements.get(pkg, pkg)
                if not m.check(pkg):
                    sh(*cmd, pkg)
                    m.add(pkg)

    # Load plugins. "Plugins" are not plugin packages, but modules
    # which we expect to live in plugin packages. Afterwards
    # 'cfg.loaded' will be a mapping from plugin names to module
    # objects.
    cfg.loaded = config()
    for import_spec in yield_plugin_import_specs(cfg):
        load_plugin(cfg, import_spec)

    # Also load global plugins
    sys.path.insert(
        0, os.path.abspath(interpolate1(cfg.spin.spin_global_plugins))
    )
    for ep in entrypoints.get_group_all("spin.plugin"):
        load_plugin(cfg, ep.module_name)

    # Create a topologically sorted list of the plugins by their
    # 'requires' dependencies. This will be used later by 'toporun' to
    # run initialization functions in order (e.g. a tool like 'flake8'
    # requires a virtualenv where it can be installed; the virtualenv
    # is provided by the 'virtualenv' plugin, which in turn requires
    # 'python', which provides a Python installation).
    nodes = cfg.loaded.keys()
    graph = {
        n: getattr(mod.defaults, "requires", [])
        for n, mod in cfg.loaded.items()
    }
    cfg.topo_plugins = reverse_toposort(nodes, graph)

    # Add command line settings.
    for prop in properties:
        k, v = prop.split("=")
        path = list(k.split("."))
        scope = cfg
        while len(path) > 1:
            scope = getattr(scope, path.pop(0))
        setattr(scope, path[0], v)

    # Run 'configure' hooks of plugins
    toporun(cfg, "configure")

    # We do this before 'debug' so people see the cruise config
    cruise.build_cruises(cfg)
    return cfg
