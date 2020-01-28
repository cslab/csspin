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
from .util import (
    config,
    echo,
    cd,
    mkdir,
    load_config,
    merge_config,
    die,
    memoizer,
    sh,
)


DEFAULTS = config(
    spin=config(
        spinfile="spinfile.yaml",
        plugin_dir=".spin",
        plugin_packages=[],
        userprofile="{HOME}/.spin",
    ),
    requirements=[],
    quiet=False,
)


def find_spinfile(spinfile_):
    """Find a file 'spinfile_' by walking up the directory tree."""
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
    merge_config(data, DEFAULTS)
    return data


def load_plugin(cfg, pi):
    if pi not in cfg.loaded:
        mod = importlib.import_module(pi)
        modcfg = getattr(mod, "defaults", config())
        target = cfg.setdefault(pi, config())
        mod.config = cfg
        merge_config(target, modcfg)
        cfg.loaded[pi] = mod
        for requirement in getattr(mod, "requires", []):
            load_plugin(cfg, requirement)


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
            default=DEFAULTS.spin.spinfile,
            type=click.Path(dir_okay=False, exists=False),
        ),
        click.option(
            "--plugin-directory",
            "-p",
            "plugin_dir",
            type=click.Path(file_okay=False, exists=False),
        ),
        click.option("--quiet", "-q", is_flag=True, default=DEFAULTS.quiet,),
        click.option("--debug", is_flag=True, default=False),
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
def cli(ctx, cwd, spinfile, plugin_dir, quiet, debug):
    # We want to honor the 'quiet' flag even if the configuration tree
    # has not yet been created.
    util.CONFIG.quiet = quiet

    # Find a project file and load it.
    if cwd:
        cd(cwd)
    else:
        spinfile = find_spinfile(spinfile)
    cfg = util.CONFIG = read_spinfile(spinfile)
    cfg.quiet = quiet
    cfg.spin.spinfile = spinfile
    cfg.spin.project_root = "."

    # We have a proper config tree now in util.CONFIG (and an alias
    # 'cfg' for it); cd to project root and proceed.
    spinfile_dir = os.path.dirname(cfg.spin.spinfile)
    cd(spinfile_dir)

    # Setup plugin_dir, where spin installs plugin packages.
    if plugin_dir:
        cfg.spin.plugin_dir = plugin_dir
    if not os.path.isabs(cfg.spin.plugin_dir):
        cfg.spin.plugin_dir = os.path.abspath(
            os.path.join(spinfile_dir, cfg.spin.plugin_dir)
        )
    if not os.path.exists(cfg.spin.plugin_dir):
        mkdir(cfg.spin.plugin_dir)
    sys.path.insert(0, cfg.spin.plugin_dir)

    with memoizer("{spin.plugin_dir}/packages.memo") as m:
        for pkg in cfg.spin.plugin_packages:
            if not m.check(pkg):
                sh(
                    "{sys.executable}",
                    "-m",
                    "pip",
                    "install",
                    "-t",
                    "{spin.plugin_dir}",
                    "{pkg}",
                )
                m.add(pkg)

    # Load plugins
    cfg.loaded = config()
    for pi in cfg.plugins:
        load_plugin(cfg, pi)

    nodes = cfg.loaded.keys()
    graph = dict(
        (n, getattr(mod, "requires", [])) for n, mod in cfg.loaded.items()
    )
    cfg.topo_plugins = toposort(nodes, graph)
    if debug:
        echo("Configuration tree (debug):")
        pprint(cfg)
    commands.main(args=ctx.args)


def toporun(ctx, *fn_names):
    cfg = ctx.obj
    for func_name in fn_names:
        for pi_name in cfg.topo_plugins:
            pi_mod = cfg.loaded[pi_name]
            initf = getattr(pi_mod, func_name, None)
            if initf:
                initf(ctx)


@click.group()
@base_options
@click.pass_context
def commands(ctx, **kwargs):
    ctx.obj = util.CONFIG
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
    pprint(ctx.obj)
