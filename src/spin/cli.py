# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""Spin automates the provisioning of tools and other development
requirements and provides shrink-wrapped project workflows.

Spin requires a 'spinfile.yaml' in the project's top-level
directory. It can be started from anywhere in the project tree, and
searches the path up for 'spinfile.yaml'. Subcommands are provided by
"plugins" declared in spinfile.yaml.

"""

import base64
import glob
import hashlib
import importlib
import logging
import os
import site
import sys

import click
import entrypoints
import packaging.version
from packaging import tags

if sys.version_info < (3, 8):  # pragma: no cover (<PY38)
    import importlib_metadata
else:  # pragma: no cover (PY38+)
    import importlib.metadata as importlib_metadata

from . import (
    cd,
    config,
    cruise,
    die,
    exists,
    get_requires,
    get_tree,
    interpolate1,
    memoizer,
    mkdir,
    readtext,
    readyaml,
    rmtree,
    schema,
    set_tree,
    sh,
    toporun,
    tree,
    warn,
    writetext,
)

N = os.path.normcase


# These are the basic defaults for the top-level configuration
# tree. Sections and values will be added by loading plugins and
# reading the project configuration file (spinfile.yaml).
DEFAULTS = config(
    spin=config(
        spinfile="spinfile.yaml",
        cache=N("{SPIN_CACHE}"),
        config=N("{SPIN_CONFIG}"),
        extra_index=None,
    ),
    quiet=False,
    verbose=0,
    cruise=config(
        # We'll have to use a dict literal here, since the keys are
        # not valid Python identifiers.
        {
            "@docker": config(executor=cruise.DockerExecutor),
            "@host": config(executor=cruise.HostExecutor),
        }
    ),
    platform=config(
        exe=".exe" if sys.platform == "win32" else "",
        shell="{SHELL}",
        tag=next(tags.sys_tags()).platform,
    ),
)


def find_spinfile(spinfile):
    """Find a file 'spinfile' by walking up the directory tree."""
    cwd = os.getcwd()
    if spinfile is None:
        spinfile = DEFAULTS.spin.spinfile
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


def load_plugin(cfg, import_spec, package=None, indent="  "):
    """Recursively load a plugin module.

    Load the plugin given by 'import_spec' and its dependencies
    specified in the module-level configuration key 'requires' (list
    of absolute or relative import specs).

    """
    if package:
        logging.debug(f"{indent}import plugin {import_spec} from {package}")
    else:
        logging.debug(f"{indent}import plugin {import_spec}")

    try:
        mod = importlib.import_module(import_spec, package)
    except ModuleNotFoundError as ex:
        warn(f"Plugin {import_spec} could not be loaded, it may need to be provisioned")
        # We tolerate this only when --cleanup and not --provision
        if not cfg.cleanup or cfg.provision:
            raise ex

    full_name = mod.__name__
    if full_name not in cfg.loaded:
        # This plugin module has not been imported so far --
        # initialize it and recursively load dependencies
        cfg.loaded[full_name] = mod
        plugin_defaults = getattr(mod, "defaults", config())
        # The subtree is either the module name for the plugin
        # (excluding the package prefix), or __name__, if that is set.
        settings_name = plugin_defaults.get("__name__", full_name.split(".")[-1])
        logging.debug(f"{indent}add subtree {settings_name}")
        plugin_config_tree = cfg.setdefault(settings_name, config())
        if plugin_defaults:
            tree.tree_set_keyinfo(
                cfg,
                settings_name,
                tree.tree_keyinfo(plugin_defaults, list(plugin_defaults.keys())[0]),
            )
        tree.tree_merge(plugin_config_tree, plugin_defaults)
        dependencies = [
            load_plugin(cfg, requirement, mod.__package__, indent=indent + "  ")
            for requirement in get_requires(plugin_config_tree, "spin")
        ]
        plugin_config_tree._requires = [dep.__name__ for dep in dependencies]
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
            "--version",
            "version",
            is_flag=True,
            help="Display spin's version and exit.",
        ),
        click.option(
            "--change-directory",
            "-C",
            "cwd",
            type=click.Path(file_okay=False, exists=True),
            help=(
                "Change directory before doing anything else. "
                "In this case, the configuration file "
                "(spinfile.yaml) is expected to live in the "
                "directory changed to."
            ),
        ),
        click.option(
            "--env",
            "envbase",
            type=click.Path(file_okay=False, exists=False),
            help=(
                "Where spin puts the environment"
                # FIXME: add documentation
            ),
        ),
        click.option(
            "--change-directory",
            "-C",
            "cwd",
            type=click.Path(file_okay=False, exists=True),
            help=(
                "Change directory before doing anything else. "
                "In this case, the configuration file "
                "(spinfile.yaml) is expected to live in the "
                "directory changed to."
            ),
        ),
        click.option(
            "-f",
            "spinfile",
            default=None,
            type=click.Path(dir_okay=False, exists=False),
            help=(
                "An alternative name for the configuration file. "
                "This can be a relative or absolute path when "
                "used without -C."
            ),
        ),
        click.option(
            "--quiet",
            "-q",
            is_flag=True,
            default=DEFAULTS.quiet,
            help=(
                "Be more quiet. By default, spin will echo commands as they are"
                " executed. With -q, no commands will be shown. The quiet option is"
                " also available to plugins via {quiet}. Some plugins will pass on the"
                " (equivalent of a) quiet option to the commands they call."
            ),
        ),
        click.option(
            "--verbose",
            "-v",
            count=True,
            default=DEFAULTS.verbose,
            help=(
                "Be more verbose. By default, spin will generate no output, except the"
                " commands it executes. Using -v, the verbosity is increased."
            ),
        ),
        click.option(
            "--debug",
            is_flag=True,
            default=False,
            help=(
                "Dump the configuration tree before processing starts. This is useful"
                " to analyze problems with spinfile.yaml and for plugin developers."
            ),
        ),
        click.option(
            "--cruise",
            "-c",
            "cruiseopt",
            multiple=True,
            help=(
                "Run spin in the given 'cruise' environment(s). Spin's cruise feature"
                " enables launching spin commands in other environments, e.g. a Docker"
                " container. Refer to spin's user manual for more information about"
                " 'cruise'."
            ),
        ),
        click.option(
            "--interactive",
            "-i",
            is_flag=True,
            default=False,
            help=(
                "Run Docker-based cruises interactively by passing '-it' to the Docker"
                " command. This option is only relevant together with the -c/--cruise"
                " option."
            ),
        ),
        click.option(
            "-p",
            "properties",
            multiple=True,
            help=(
                "Override a setting in spin's configuration tree, using"
                " 'property=value'. This only works for string properties. Example:"
                " spin -p python.version=3.9.6 ..."
            ),
        ),
        click.option(
            "--provision",
            is_flag=True,
            default=False,
            help=(
                "Create or update a development environment. This option can be used"
                " without a command, to only provision an environment. When used with a"
                " command, the environment will be created or updated, and the command"
                " will run afterwards."
            ),
        ),
        click.option(
            "--cleanup",
            is_flag=True,
            default=False,
            help=(
                "Clean up project-local stuff that has been provisioned by spin, e.g."
                " virtual environments and {project_root}/.spin. This will not clean"
                " global caches. '--cleanup' can be combined with '--provision',"
                " tearing down and re-provisioning the development environment in one"
                " step."
            ),
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


NOENV_COMMANDS = set()


def register_noenv(cmdname):
    global NOENV_COMMANDS
    NOENV_COMMANDS.add(cmdname)


_nested = False


@click.command(cls=GroupWithAliases, help=__doc__)
# Note that the base_options here are not actually used and ignore by
# 'commands'. Base options are processed by 'cli'.
@base_options
@click.pass_context
def commands(ctx, **kwargs):
    global _nested
    cfg = ctx.obj = get_tree()
    if not _nested:
        if ctx.invoked_subcommand not in NOENV_COMMANDS:
            if not exists(cfg.spin.env_base):
                die(
                    "This project has not yet been provisioned. You "
                    "may want to run spin with the --provison flag."
                )
            toporun(ctx.obj, "init")
        _nested = True


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
    version,
    cwd,
    envbase,
    spinfile,
    quiet,
    verbose,
    debug,
    cruiseopt,
    interactive,
    properties,
    provision,
    cleanup,
):
    if verbose > 1:
        # Set up logging
        logging.basicConfig(level=logging.DEBUG)

    # We want to honor the 'quiet' and 'verbose' flags early, even if
    # the configuration tree has not yet been created, as subsequent
    # code uses 'echo' and/or 'log'.
    get_tree().quiet = quiet
    get_tree().verbose = verbose

    # When the output is redirected, set quiet
    if os.fstat(0) != os.fstat(1):
        quiet = get_tree().quiet = True

    if version:
        print(importlib_metadata.version("spin"))
        return 0

    # Find a project file and load it.
    if cwd:
        cd(cwd)
    else:
        _spinfile = find_spinfile(spinfile)
        if spinfile and not _spinfile:
            die(f"{spinfile} not found")
        spinfile = _spinfile

    cfg = load_config_tree(
        spinfile, cwd, envbase, quiet, verbose, cleanup, provision, properties
    )

    mkdir("{spin.cache}")

    # Debug aid: dump config tree when given --debug; if nothing else
    # is requested ... that's it!
    if debug:
        print(tree.tree_dump(cfg))
        if not ctx.args:
            return

    if not cruiseopt:
        # When not cruising, and we have any of the provisioning
        # flags, do provisioning now.
        if cleanup:
            toporun(cfg, "cleanup", reverse=True)
            if not provision:
                # There is nothing we can meaningfully do after 'cleanup',
                # unless 'provision' is also given => so do not run any
                # tasks.
                return
        if provision:
            toporun(cfg, "provision")
            toporun(cfg, "finalize_provision")
            if not ctx.args:
                # When provisioning without a subcommand, don't run
                # into the usage.
                return
        # Invoke the main command group, which by now has all the
        # sub-commands from the plugins.
        kwargs = getattr(cli, "click_main_kwargs", {})
        commands.main(args=ctx.args, **kwargs)
    else:
        cruise.do_cruise(cfg, cruiseopt, interactive)


def find_plugin_packages(cfg):
    # Packages that are required to load plugins are identified by
    # the keys in dict-valued list items of the 'plugins' setting
    for item in cfg.get("plugin-packages", []):
        yield item


def yield_plugin_import_specs(cfg):
    for item in cfg.get("plugins", []):
        if isinstance(item, dict):
            for package, modules in item.items():
                for module in modules:
                    yield f"{package}.{module}"
        else:
            yield item


def load_config_tree(
    spinfile,
    cwd=False,
    envbase=None,
    quiet=False,
    verbose=False,
    cleanup=False,
    provision=False,
    properties=(),
):
    logging.info(f"Loading {spinfile}")
    spinschema = schema.schema_load(
        os.path.join(os.path.dirname(__file__), "schema.yaml")
    )
    cfg = spinschema.get_default()
    set_tree(cfg)
    cfg.schema = spinschema
    userdata = readyaml(spinfile) if spinfile else config()
    tree.tree_update(cfg, userdata)
    tree.tree_merge(cfg, DEFAULTS)

    # Merge user-specific globals if they exist
    if exists("{spin.spin_global}"):
        logging.debug(
            f"Merging user settings from {interpolate1('{spin.spin_global}')}"
        )
        tree.tree_update(cfg, readyaml(interpolate1("{spin.spin_global}")))

    if envbase:
        cfg.spin.env_base = envbase

    # Reflect certain command line options in the config tree.
    cfg.quiet = quiet
    cfg.verbose = verbose
    # This is meant for tools that support -q; instead of
    # conditionally passing -q on the command line, plugins can simply
    # build the command using cfg.quietflag (the None will be filtered
    # out by spin.interpolate)
    cfg.quietflag = None if cfg.verbose else "-q"

    cfg.spin.spinfile = spinfile
    cfg.cleanup = cleanup
    cfg.provision = provision

    # We have a proper config tree now in 'cfg'; cd to project root
    # and proceed.
    if spinfile:

        # Check spin version requested by this spinfile
        minspin = getattr(cfg, "minimum-spin", None)
        if not minspin:
            die("spin requires 'minimum-spin' to be set")
        minspin = packaging.version.parse(minspin)
        spinversion = packaging.version.parse(importlib_metadata.version("spin"))
        if minspin > spinversion:
            die(f"this project requires spin>={minspin} (spin version {spinversion})")

        cfg.spin.project_root = os.path.dirname(os.path.abspath(cfg.spin.spinfile))
        if not cwd:
            cd(cfg.spin.project_root)
        cfg.spin.project_name = os.path.basename(cfg.spin.project_root)
        path_hash = hashlib.sha256(
            os.path.dirname(cfg.spin.project_root).encode()
        ).digest()
        path_hash = base64.urlsafe_b64encode(path_hash).decode()[:8]
        cfg.spin.project_hash = f"{cfg.spin.project_name}-{path_hash}"

        if not exists("{spin.spin_dir}"):
            mkdir("{spin.spin_dir}")
            writetext(
                "{spin.spin_dir}/.gitignore", "# Created by spin automatically\n*\n"
            )

        # Setup plugin_dir, where spin installs plugin packages.
        cfg.spin.plugin_dir = interpolate1(cfg.spin.plugin_dir)
        if not os.path.isabs(cfg.spin.plugin_dir):
            cfg.spin.plugin_dir = os.path.abspath(
                os.path.join(cfg.spin.project_root, cfg.spin.plugin_dir)
            )
            sys.path.insert(0, cfg.spin.plugin_dir)
        if cleanup and exists(cfg.spin.plugin_dir):
            rmtree(cfg.spin.plugin_dir)

        if provision:
            install_plugin_packages(cfg)

    for localpath in cfg.get("plugin-path", []):
        localabs = interpolate1("{spin.project_root}/" + localpath)
        if not exists(localabs):
            die(f"Plugin path {localabs} doesn't exist")
        sys.path.insert(0, localabs)

    # Load plugins. "Plugins" are not plugin packages, but modules
    # which we expect to live in plugin packages. Afterwards
    # 'cfg.loaded' will be a mapping from plugin names to module
    # objects.
    cfg.loaded = config()
    logging.debug("loading project plugins:")
    load_plugin(cfg, "spin.builtin")
    for import_spec in yield_plugin_import_specs(cfg):
        load_plugin(cfg, import_spec)

    # Also load global plugins
    sys.path.insert(0, os.path.abspath(interpolate1(cfg.spin.spin_global_plugins)))
    logging.debug("loading global plugins:")
    for ep in entrypoints.get_group_all("spin.plugin"):
        load_plugin(cfg, ep.module_name)

    # Create a topologically sorted list of the plugins by their
    # dependencies, which have been stored in "_requires" by
    # load_plugin. This will be used later by 'toporun' to run
    # initialization functions in order (e.g. a tool like 'flake8'
    # requires a virtualenv where it can be installed; the virtualenv
    # is provided by the 'virtualenv' plugin, which in turn requires
    # 'python', which provides a Python installation).
    nodes = cfg.loaded.keys()
    graph = {n: getattr(mod.defaults, "_requires", []) for n, mod in cfg.loaded.items()}
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


def install_plugin_packages(cfg):
    if not exists(cfg.spin.plugin_dir):
        mkdir(cfg.spin.plugin_dir)

    # To be able to do editable installs to plugin dir, we have to
    # temporarily set PYTHONPATH, to let the pip subprocess
    # believe plugindir is in sys.path. But we must be careful to
    # unset it before calling anything else -- see below!
    old_python_path = os.environ.get("PYTHONPATH", None)
    os.environ["PYTHONPATH"] = interpolate1(cfg.spin.plugin_dir)

    cmd = [
        f"{sys.executable}",
        "-mpip",
        "install",
        "-q" if not cfg.verbose else None,
        "-t",
        "{spin.plugin_dir}",
    ]

    if cfg.spin.extra_index:
        cmd.extend(["--extra-index-url", cfg.spin.extra_index])

    something_was_installed = False

    # Install plugin packages that are not yet installed, using pip
    # with the "-t" (target) option pointing to the plugin directory.
    with memoizer(N("{spin.plugin_dir}/packages.memo")) as m:
        replacements = cfg.get("devpackages", {})
        for pkg in find_plugin_packages(cfg):
            pkg = replacements.get(pkg, pkg)
            if not m.check(pkg):
                something_was_installed = True
                args = list(cmd)
                args.extend(pkg.split())
                sh(*args)
                m.add(pkg)

    # Now remove PYTHONPATH and make plugin a pth-enabled part of
    # sys.path
    if old_python_path:
        os.environ["PYTHONPATH"] = old_python_path
    else:
        del os.environ["PYTHONPATH"]

    if something_was_installed:
        # Now it becomes a little dirty: pip did not write
        # easy-install.pth while installing plugin packages to the
        # plugin dir: fix it up, in case some plugin packages had been
        # installed editable.
        easy_install = []
        for egg_link in glob.iglob(interpolate1("{spin.plugin_dir}/*.egg-link")):
            easy_install.append(readtext(egg_link).splitlines()[0])
        writetext("{spin.plugin_dir}/easy-install.pth", "\n".join(easy_install))

    site.addsitedir(cfg.spin.plugin_dir)
