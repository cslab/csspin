# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""Spin automates the provisioning of tools and other development
requirements and provides shrink-wrapped project workflows.

Spin requires a ``spinfile.yaml`` in the project's top-level directory. It can
be started from anywhere in the project tree, and searches the path up for
``spinfile.yaml``. Subcommands are provided by "plugins" declared in
``spinfile.yaml``.

Spin also leverages `click's <https://click.palletsprojects.com/en/8.0.x/>`_
feature set, enabling the usage of environment variables instead of CLI flags
and options (see :ref:`environment-as-input-channel-label`).
"""

from __future__ import annotations

import glob
import importlib
import importlib.metadata as importlib_metadata
import os
import sys
from site import addsitedir
from types import ModuleType
from typing import TYPE_CHECKING, Any, Generator, Iterable

import click
import entrypoints
import packaging.version
from path import Path

from spin import (
    Verbosity,
    cd,
    config,
    debug,
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
    setenv,
    sh,
    toporun,
    tree,
    warn,
    writetext,
)
from spin.tree import ConfigTree

if TYPE_CHECKING:
    from typing import Callable


# These are the basic defaults for the top-level configuration
# tree. Sections and values will be added by loading plugins and
# reading the project configuration file (spinfile.yaml).
DEFAULTS = config(
    spin=config(
        spinfile="spinfile.yaml",
        cache=Path("{SPIN_CACHE}"),
        data=Path("{SPIN_DATA}"),
        config=Path("{SPIN_CONFIG}"),
        extra_index=None,
        version=importlib_metadata.version("cs.spin"),
    ),
    platform=config(
        exe=".exe" if sys.platform == "win32" else "",
        shell=os.getenv("SHELL"),
        kind=sys.platform,
    ),
)


def find_spinfile(spinfile: str | None) -> str | None:
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


def load_plugin(
    cfg: tree.ConfigTree,
    import_spec: str,
    may_fail: bool = False,
    indent: str = "  ",
) -> ModuleType | None:
    """Recursively load a plugin module.

    Load the plugin given by 'import_spec' and its dependencies
    specified in the module-level configuration key 'requires' (list
    of absolute or relative import specs).

    """
    debug(f"{indent}import plugin {import_spec}")

    mod = full_name = None
    try:
        # Invalidate the caches before dynamically importing modules that were
        # created after the interpreter was started.
        importlib.invalidate_caches()
        mod = importlib.import_module(import_spec)
        full_name = mod.__name__
    except ModuleNotFoundError as ex:
        warn(f"Plugin {import_spec} could not be loaded, it may need to be provisioned")
        # We tolerate this only in context of cleanup, where imports may not
        # succeed.
        if not may_fail:
            raise ex

    if full_name and full_name not in cfg.loaded:
        # This plugin module has not been imported so far --
        # initialize it and recursively load dependencies

        plugin_defaults = getattr(mod, "defaults", config())
        # The subtree is either the module name for the plugin
        # (excluding the package prefix), or __name__, if that is set.
        settings_name = plugin_defaults.get("__name__", full_name.split(".")[-1])
        debug(f"{indent}add subtree {settings_name}")
        plugin_config_tree = cfg.setdefault(settings_name, config())
        if not isinstance(plugin_config_tree, ConfigTree):
            die(
                f"The configuration of {import_spec} is invalid."
                " Please check its configuration in spinfile.yaml"
                " and global.yaml."
            )

        if not import_spec.startswith("spin."):
            try:
                # Load the plugin specific schema for non-builtin plugins
                plugin_name = import_spec.split(".")[-1]
                debug(f"{indent}loading {plugin_name}_schema.yaml")
                plugin_schema = schema.schema_load(  # type: ignore[attr-defined]
                    os.path.join(
                        os.path.dirname(mod.__file__),  # type: ignore[union-attr,arg-type]
                        f"{plugin_name}_schema.yaml",
                    )
                ).properties[plugin_name]
                schema_defaults = plugin_schema.get_default()
                plugin_config_tree.schema = plugin_schema
                tree.tree_merge(plugin_config_tree, schema_defaults)
            except FileNotFoundError:
                warn(f"Plugin {import_spec} does not provide a schema.")
            except KeyError:
                warn(f"Plugin {import_spec} does not provide a valid schema.")

            if plugin_defaults:
                tree.tree_update(
                    plugin_config_tree,
                    plugin_defaults,  # type: ignore[arg-type]
                    keep=interpolate1("{spin.spinfile}"),
                )
        elif plugin_defaults:
            tree.tree_update(
                plugin_config_tree,
                plugin_defaults,  # type: ignore[arg-type]
                keep=interpolate1("{spin.spinfile}"),
            )
        tree.tree_apply_directives(plugin_config_tree)

        cfg.loaded[full_name] = mod
        dependencies = set()
        for requirement in get_requires(plugin_config_tree, "spin"):
            if plugin := load_plugin(
                cfg, requirement, may_fail=may_fail, indent=indent + "  "
            ):
                # Only depend on installed plugins; This is sufficient here,
                # since a plugin can only be absent if may_fail is set.
                dependencies.add(plugin)

        plugin_config_tree._requires = [  # pylint: disable=protected-access
            dep.__name__
            for dep in dependencies  # pylint: disable=protected-access # noqa: E501
        ]
        mod.defaults = plugin_config_tree  # type: ignore[union-attr]
    return mod


def reverse_toposort(nodes: Iterable, graph: dict) -> list:
    """Topologically sort nodes according to graph, which is a dict
    mapping nodes to dependencies.
    """
    graph = dict(graph)  # don't destroy the input
    counts = {n: 0 for n in nodes}
    for targets in graph.values():
        for n in targets:
            counts[n] += 1
    result = []  # type: ignore[var-annotated]
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
def base_options(fn: Callable) -> Callable:
    decorators = [
        click.option(
            "--version",
            "version",
            is_flag=True,
            help="Display spin's version and exit.",
        ),
        click.option(
            "--help",
            is_flag=True,
            help="Display spin's help and exit.",
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
                "Set an alternative directory for the environment instead of the name"
                " computed by spin (SPIN_ENVBASE)."
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
            default=False,
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
            default=0,
            help=(
                "Be more verbose. By default, spin will generate no output, except the"
                " commands it executes. Using -v, the verbosity is increased."
            ),
        ),
        click.option(
            "--dump",
            is_flag=True,
            default=False,
            help=(
                "Dump the configuration tree before processing starts. This is useful"
                " to analyze problems with spinfile.yaml and for plugin developers."
            ),
        ),
        click.option(
            "--prepend-properties",
            "--pp",
            multiple=True,
            help=(
                "Prepend to a setting in spin's configuration tree, using"
                " 'property=value'. This only works for prepending to lists."
                " Example: spin --pp pytest.opts=\"-m 'not slow'\""
            ),
        ),
        click.option(
            "--append-properties",
            "--ap",
            multiple=True,
            help=(
                "Append to a setting in spin's configuration tree, using"
                " 'property=value'. This only works for appending to lists."
                " Example: spin --ap pytest.opts=['-vv', '']"
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
    for decorator in decorators:
        fn = decorator(fn)
    return fn


class GroupWithAliases(click.Group):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        click.Group.__init__(self, *args, **kwargs)
        self._aliases: dict = {}

    def register_alias(self, alias: str, cmd_object: click.Command) -> None:
        self._aliases[alias] = cmd_object

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command:
        cmd = click.Group.get_command(self, ctx, cmd_name)
        if cmd is None:
            cmd = self._aliases.get(cmd_name, None)
        return cmd


NOENV_COMMANDS = set()


def register_noenv(cmdname: str) -> None:
    NOENV_COMMANDS.add(cmdname)


_nested = False


@click.command(cls=GroupWithAliases, help=__doc__)
# Note that the base_options here are not actually used and ignore by
# 'commands'. Base options are processed by 'cli'.
@base_options
@click.pass_context
def commands(ctx: click.Context, **kwargs: Any) -> None:
    global _nested  # pylint: disable=global-statement
    cfg = ctx.obj = get_tree()
    if not _nested:
        if ctx.invoked_subcommand not in NOENV_COMMANDS:
            if not exists(cfg.spin.spin_dir):
                die(
                    "This project has not yet been provisioned. You "
                    "may want to run spin with the --provision flag."
                )
            toporun(ctx.obj, "init")
        _nested = True


@click.command(
    context_settings={
        "allow_extra_args": True,
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
def cli(  # type: ignore[return] # pylint: disable=too-many-arguments,too-many-return-statements
    ctx: click.Context,
    version: packaging.version.Version | None,
    help: bool,  # pylint: disable=W0622
    cwd: str,
    envbase: str,
    spinfile: str,
    quiet: bool,
    verbose: int,
    dump: bool,
    properties: tuple,
    prepend_properties: tuple,
    append_properties: tuple,
    provision: bool,
    cleanup: bool,
) -> int | None:
    if version:
        print(importlib_metadata.version("cs.spin"))
        return 0

    if quiet:
        verbose = -1
    elif ctx.args and ctx.args[0] in ("env", "system-provision"):
        # Special case for 'env' and 'system-provision:
        quiet = True
        verbose = -1

    if system_provision := (ctx.args and ctx.args[0] == "system-provision"):
        # --cleanup and --provision are disabled when calling system-provision
        # since we do not want a full provision, as we only need to pull the
        # plugin-packages without provisioning plugins. We also do not want
        # cleanup, as we depend on the existence of the plugin-packages when
        # calling the system-provision task.
        cleanup = False
        provision = False

    verbosity = Verbosity(verbose)
    # We want to honor the '--quiet' and '--verbose' flags early, even if
    # the configuration tree has not yet been created, as subsequent
    # code uses 'echo' and/or 'log'.
    get_tree().verbosity = verbosity

    # Find a project file and load it.
    if cwd:
        cd(cwd)
    _spinfile = find_spinfile(spinfile)
    if not _spinfile:
        if help:
            warn("No configuration file found")
            commands.main(args=ctx.args)
            return None
        elif spinfile:
            die(f"{spinfile} not found")
        else:
            die("No configuration file found")
    spinfile = _spinfile  # type: ignore[assignment]

    try:
        cfg = load_config_tree(
            spinfile=spinfile,
            cwd=cwd,
            envbase=envbase,
            verbosity=verbosity,
            cleanup=cleanup,
            provision=provision,
            system_provision=system_provision,  # type: ignore[arg-type]
            properties=properties,
            prepend_properties=prepend_properties,
            append_properties=append_properties,
        )
    except ModuleNotFoundError as exc:
        if help:
            commands.main(args=ctx.args)
            return None
        die(exc)

    mkdir("{spin.cache}")
    mkdir("{spin.data}")

    # dump config tree when given --dump; if nothing else is requested ...
    # that's it!
    if dump:
        print(tree.tree_dump(cfg))
        if not ctx.args and not provision:
            return None

    # Cleanup. Will also try to load plugins and call their cleanup hooks.
    if cleanup:
        toporun(cfg, "cleanup", reverse=True)
        rmtree(cfg.spin.spin_dir / "plugins")
        if not provision:
            # There is nothing we can meaningfully do after 'cleanup',
            # unless 'provision' is also given => so do not run any
            # tasks.
            return None

    # Provision. Will reload the tree, if the plugins have been
    # deleted before.
    if provision:
        # Reget the plugins and reload the tree, if cleaned up before.
        if cleanup:
            cfg = load_config_tree(
                spinfile=spinfile,
                cwd=cwd,
                envbase=envbase,
                verbosity=verbosity,
                cleanup=False,
                provision=provision,
                system_provision=False,
                properties=properties,
                prepend_properties=prepend_properties,
                append_properties=append_properties,
            )
        toporun(cfg, "provision")
        toporun(cfg, "finalize_provision")
        if not ctx.args:
            # When provisioning without a subcommand, don't run
            # into the usage.
            return None

    # Invoke the main command group, which by now has all the
    # sub-commands from the plugins.
    kwargs = getattr(cli, "click_main_kwargs", {})
    kwargs["complete_var"] = "_SPIN_COMPLETE"
    commands.main(args=ctx.args, **kwargs)


def find_plugin_packages(cfg: tree.ConfigTree) -> Generator:
    # Packages that are required to load plugins are identified by
    # the keys in dict-valued list items of the 'plugins' setting
    plugin_packages = cfg.get("plugin-packages", [])
    if not isinstance(plugin_packages, list):
        die("'plugin-packages' configuration is invalid!")
    yield from plugin_packages


def yield_plugin_import_specs(cfg: tree.ConfigTree) -> Generator:
    plugins = cfg.get("plugins", [])
    if not isinstance(plugins, list):
        die("'plugins' configuration is invalid!")

    for item in plugins:
        if isinstance(item, dict):
            for package, modules in item.items():
                for module in modules:
                    yield f"{package}.{module}"
        else:
            yield item


def load_config_tree(  # pylint: disable=too-many-locals,too-many-arguments
    spinfile: str | Path,
    cwd: str = "",
    envbase: str | None = None,
    verbosity: Verbosity = Verbosity.NORMAL,
    cleanup: bool = False,
    provision: bool = False,
    system_provision: bool = False,
    properties: tuple = (),
    prepend_properties: tuple = (),
    append_properties: tuple = (),
) -> tree.ConfigTree:
    """Load the configuration and plugins from ``spinfile`` and build the tree.

    The user's global spinfile is used to extend the built tree.

    If ``provision`` is set, plugins will be provisioned.
    """
    get_tree().verbosity = verbosity
    debug(f"Loading {spinfile}")
    spinschema = schema.schema_load(Path(__file__).dirname() / "schema.yaml")

    cfg = spinschema.get_default()  # type: ignore[call-arg]
    set_tree(cfg)
    cfg.verbosity = verbosity
    cfg.schema = spinschema
    userdata = readyaml(spinfile) if spinfile else config()
    if not userdata:
        die("The spinfile seems to be invalid!")
    tree.tree_update(cfg, userdata)
    tree.tree_merge(cfg, DEFAULTS)

    # Merge user-specific globals if they exist
    if (
        not os.getenv("SPIN_DISABLE_GLOBAL_YAML")
        and (spin_global := interpolate1("{SPIN_CONFIG}/global.yaml"))
        and exists(spin_global)
    ):
        user_settings = readyaml(spin_global)
        if user_settings:
            debug(f"Merging user settings from {os.path.normpath(spin_global)}")
            tree.tree_update(cfg, user_settings)

    if envbase:
        cfg.spin.spin_dir = Path(envbase).absolute() / ".spin"

    cfg.spin.spinfile = Path(spinfile)
    cfg.spin.project_root = Path(cfg.spin.spinfile).absolute().normpath().dirname()
    cfg.spin.project_name = cfg.spin.project_root.basename()
    cfg.spin.launch_dir = Path().cwd().relpath(cfg.spin.project_root)
    cfg.spin.spin_dir = interpolate1(Path(cfg.spin.spin_dir)).absolute()  # type: ignore[union-attr]

    if not cwd:
        cd(cfg.spin.project_root)

    if not exists(cfg.spin.spin_dir):
        mkdir(cfg.spin.spin_dir)
        writetext(
            cfg.spin.spin_dir / ".gitignore",
            "# Created by spin automatically\n*\n",
        )

    sys.path.insert(0, str(interpolate1(cfg.spin.spin_dir / "plugins")))

    setenv(**cfg.environment)

    if (provision or system_provision) and not cleanup:
        # if cleanup == true, we're fine with whatever plugins we
        # have right now. So no need to waste our time pulling new
        # stuff here.
        install_plugin_packages(cfg)

    plugin_path = cfg.get("plugin-path", [])
    if not isinstance(plugin_path, list):
        die("'plugin-path' configuration is invalid!")

    for localpath in plugin_path:
        localabs = interpolate1(cfg.spin.project_root / localpath)
        if not exists(localabs):
            die(f"Plugin path {localabs} doesn't exist")
        sys.path.insert(0, localabs)

    # Load plugins. "Plugins" are not plugin packages, but modules
    # which we expect to live in plugin packages. Afterwards
    # 'cfg.loaded' will be a mapping from plugin names to module
    # objects.
    cfg.loaded = config()
    addsitedir(cfg.spin.spin_dir / "plugins")
    debug("loading project plugins:")
    load_plugin(cfg, "spin.builtin", may_fail=cleanup)
    for import_spec in yield_plugin_import_specs(cfg):
        load_plugin(cfg, import_spec, may_fail=cleanup)

    # Also load global plugins
    sys.path.insert(
        0,
        str(interpolate1(Path(cfg.spin.cache)).absolute() / "plugins"),  # type: ignore[union-attr]
    )
    sys.path.insert(
        0,
        str(interpolate1(Path(cfg.spin.data)).absolute() / "plugins"),  # type: ignore[union-attr]
    )
    debug("loading global plugins:")
    for ep in entrypoints.get_group_all("spin.plugin"):
        load_plugin(cfg, ep.module_name, may_fail=cleanup)

    # Create a topologically sorted list of the plugins by their
    # dependencies, which have been stored in "_requires" by
    # load_plugin. This will be used later by 'toporun' to run
    # initialization functions in order (e.g. a tool like 'flake8'
    # requires a virtualenv where it can be installed; the virtualenv
    # is provided by the 'virtualenv' plugin, which in turn requires
    # 'python', which provides a Python installation).
    nodes = cfg.loaded.keys()
    graph = {n: getattr(mod.defaults, "_requires", []) for n, mod in cfg.loaded.items()}
    cfg.spin.topo_plugins = reverse_toposort(nodes, graph)

    # Update properties modified via: -p, --pp, --ap and the environment
    tree.tree_update_properties(
        cfg,
        properties,
        prepend_properties,
        append_properties,
    )

    if not cleanup:
        # Do not configure and sanitize in case of cleanup, since plugin
        # packages may not be installed, causing AttributeErrors in case of
        # accessing not-initialized plugins via "cfg." as well as failures due
        # to interpolation against property tree keys that does not exist.

        # Run 'configure' hooks of plugins
        toporun(cfg, "configure")

        # Interpolate values of the configuration tree and enforce their types
        tree.tree_sanitize(cfg)

    return cfg  # type: ignore[no-any-return]


def install_plugin_packages(cfg: tree.ConfigTree) -> None:
    """Install plugin packages which are not yet installed and extend the
    configuration tree.
    """
    mkdir(plugin_dir := interpolate1(Path("{spin.spin_dir}") / "plugins"))

    # To be able to do editable installs to plugin dir, we have to
    # temporarily set PYTHONPATH, to let the pip subprocess
    # believe plugin_dir is in sys.path. But we must be careful to
    # unset it before calling anything else -- see below!
    old_python_path = os.environ.get("PYTHONPATH", None)
    os.environ["PYTHONPATH"] = plugin_dir

    cmd = [
        f"{sys.executable}",
        "-mpip",
        "install",
        "-q" if cfg.verbosity < Verbosity.INFO else None,
        "--disable-pip-version-check",
        "-t",
        plugin_dir,
        "--index-url",
        "{spin.index_url}",
    ]

    if cfg.spin.extra_index:
        cmd.extend(["--extra-index-url", cfg.spin.extra_index])

    something_was_installed = False

    # Install all missing plugin-packages at once to avoid pip's dependency
    # resolver to fail without exit-zero, while using the "-t" (target) option
    # pointing to the plugin directory.
    with memoizer(plugin_dir / "packages.memo") as m:  # type: ignore[operator]
        if to_be_installed := set(find_plugin_packages(cfg)):
            something_was_installed = True
            args = list(cmd)
            for pkg in to_be_installed:
                args.extend(pkg.split())
            sh(*args)
            for pkg in to_be_installed:
                m.add(pkg)

    # Now remove PYTHONPATH and make plugin a pth-enabled part of sys.path
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
        for egg_link in glob.iglob(plugin_dir / "*.egg-link"):  # type: ignore[operator]
            easy_install.append(readtext(egg_link).splitlines()[0])
        writetext(plugin_dir / "easy-install.pth", "\n".join(easy_install))  # type: ignore[operator]
