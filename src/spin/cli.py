# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys
from pprint import pprint
import importlib

import click
from . import util
from .util import config, echo, cd, mkdir, load_config, merge_config, die
from . import defaults


def find_spinfile(spinfile_):
    cwd = os.getcwd()
    spinfile = spinfile_
    while not os.path.exists(spinfile):
        cwd_ = os.path.dirname(cwd)
        if cwd_ == cwd:
            break
        cwd = cwd_
        spinfile = os.path.join(cwd, spinfile_)
    if os.path.exists(spinfile):
        return os.path.abspath(spinfile)
    die(f"{spinfile_} not found")


def read_spinfile(spinfile):
    data = load_config(spinfile)
    merge_config(data, defaults.DEFAULTS)
    return data


def toposort(nodes, graph):
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
        raise Exception("dependency graph has at least one cycle")

    return result


def base_options(fn):
    decorators = [
        click.option(
            "--change-directory",
            "-C",
            "cwd",
            type=click.Path(file_okay=False, exists=True),
        ),
        click.option(
            "-f",
            "spinfile",
            default=defaults.DEFAULTS.spin.spinfile,
            type=click.Path(dir_okay=False, exists=False),
        ),
        click.option(
            "--plugin-directory",
            "-p",
            "plugin_dir",
            type=click.Path(file_okay=False, exists=False),
        ),
        click.option(
            "--quiet", "-q", is_flag=True, default=defaults.DEFAULTS.quiet,
        ),
    ]
    for d in decorators:
        fn = d(fn)
    return fn


@click.command(
    context_settings=dict(
        allow_extra_args=True,
        ignore_unknown_options=True,
        help_option_names=["--hidden-help-option"],
    )
)
@base_options
@click.pass_context
def cli(ctx, cwd, spinfile, plugin_dir, quiet):
    util.GLOBALS.quiet = quiet
    if cwd:
        cd(cwd)
    else:
        spinfile = find_spinfile(spinfile)
    cfg = read_spinfile(spinfile)
    util.GLOBALS = cfg
    util.GLOBALS.quiet = quiet
    spinfile_dir = os.path.dirname(spinfile)
    cd(spinfile_dir)
    cfg.spin.spinfile = spinfile
    cfg.spin.project_root = "."
    if plugin_dir:
        cfg.spin.plugin_dir = plugin_dir
    if not os.path.isabs(cfg.spin.plugin_dir):
        cfg.spin.plugin_dir = os.path.abspath(
            os.path.join(spinfile_dir, cfg.spin.plugin_dir)
        )
    if not os.path.exists(cfg.spin.plugin_dir):
        mkdir(cfg.spin.plugin_dir)
    sys.path.insert(0, cfg.spin.plugin_dir)
    # FIXME: Check wether all packages in plugin_dir are installed.
    # we're using a rather lousy heuristic of checking for directory
    # named like the packages -- to be fixed if required ...
    existing = set(os.listdir(cfg.spin.plugin_dir))
    required = set(cfg.spin.plugin_packages)
    to_be_installed = required - existing
    if to_be_installed:
        echo(f"Installing plugin packages {to_be_installed}")
        # FIXME: this should be 'sh' from util ...
        # 2nd FIXME: should this be pip from the spin install??
        os.system(
            f"pip install -t {cfg.spin.plugin_dir} "
            "{' '.join(to_be_installed)}"
        )

    def load_plugin(pi):
        if pi not in plugins:
            # echo(f"loading {pi}")
            mod = importlib.import_module(pi)
            modcfg = getattr(mod, "defaults", config())
            target = cfg.setdefault(pi, config())
            mod.config = cfg
            merge_config(target, modcfg)
            plugins[pi] = mod
            for requirement in getattr(mod, "requires", []):
                load_plugin(requirement)

    # Load all the plugins and their configuration data
    plugins = config()
    for pi in cfg.plugins:
        load_plugin(pi)
    cfg.plugins = plugins
    nodes = cfg.plugins.keys()
    graph = dict(
        (n, getattr(mod, "requires", [])) for n, mod in cfg.plugins.items()
    )
    cfg.topo_plugins = toposort(nodes, graph)
    commands.main(args=ctx.args)


def toporun(ctx, *fn_names):
    cfg = ctx.obj
    for func_name in fn_names:
        for pi_name in cfg.topo_plugins:
            pi_mod = cfg.plugins[pi_name]
            initf = getattr(pi_mod, func_name, None)
            if initf:
                initf(ctx)


@click.group()
@base_options
@click.pass_context
def commands(ctx, **kwargs):
    ctx.obj = util.GLOBALS
    toporun(ctx, "configure", "init")


@commands.command()
@click.pass_context
def help(ctx):
    print(ctx.parent.get_help())


@commands.command()
@click.pass_context
def cleanup(ctx):
    toporun(ctx, "cleanup")


@commands.command()
@click.pass_context
def dump(ctx):
    pprint(util.GLOBALS)
