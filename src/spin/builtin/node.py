# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""
This module implements the node (NodeJS) plugin for cs.spin.
"""

from __future__ import annotations

import sys
from os import symlink
from textwrap import dedent
from typing import TYPE_CHECKING

from spin import (
    Path,
    config,
    copy,
    die,
    exists,
    get_requires,
    interpolate1,
    memoizer,
    setenv,
    sh,
    writetext,
)

if TYPE_CHECKING:
    from spin.tree import ConfigTree

defaults = config(memo="{python.venv}/nodeversions.memo")


def configure(cfg: ConfigTree) -> None:
    # FIXME: Comparison to None should be done right.
    if interpolate1("{node.use}") != "None":
        cfg.node.requires.python = []

    npm = Path(cfg.python.scriptdir) / "npm"
    node = Path(cfg.python.scriptdir) / "node"

    if sys.platform == "win32":
        npm += ".cmd"
        node += "exe"

    if not exists(node) or not exists(npm):
        if cfg.node.version is None and not cfg.node.use:
            die(
                "Spin's Node.js plugin does not set a default version.\n"
                "Please choose a version in spinfile.yaml by setting node.version"
            )
        if cfg.node.version == "system":
            die("Can't use node.version=system. Try node.use instead.")

        if cfg.node.use and not exists(cfg.node.use):
            import shutil

            if not (interpreter := shutil.which(cfg.node.use)):
                die(f"Could not finde Node interpreter '{cfg.node.use}'")
            cfg.node.use = Path(interpreter)


def provision(cfg: ConfigTree, *args: str) -> None:
    npm = cfg.python.scriptdir / "npm"
    if sys.platform == "win32":
        npm += ".cmd"

    # NODE_PATH and the prefix must be defined in any case, otherwise the
    # node_modules will be placed in venv/Scripts/node_modules instead of
    # venv/Lib/node_modules.
    if sys.platform == "win32":
        npm_prefix_path = cfg.python.venv / "Lib"
        node_path = npm_prefix_path / "node_modules"
    else:
        npm_prefix_path = cfg.python.venv
        node_path = npm_prefix_path / "lib" / "node_modules"
    setenv(
        NODE_PATH=node_path,
        NPM_CONFIG_PREFIX=npm_prefix_path,
        npm_config_prefix=npm_prefix_path,
    )

    with memoizer(cfg.node.memo) as m:
        if cfg.node.use:
            node_dir = cfg.node.use.dirname()
            if sys.platform == "win32":
                copy(cfg.node.use, cfg.python.scriptdir)
                create_npm_cmd(cfg, node_dir)
            else:
                copy(cfg.node.use, cfg.python.scriptdir)
                symlink(node_dir / "npm", cfg.python.scriptdir / "npm")
            m.add(cfg.node.use)

        elif cfg.node.version in ("latest", "lts") or not m.check(cfg.node.version):
            cmd = [
                cfg.python.python,
                "-mnodeenv",
                "--python-virtualenv",
                f"--node={cfg.node.version}",
            ]
            if cfg.node.mirror:
                cmd.append(f"--mirror={cfg.node.mirror}")
            if cfg.node.ignore_ssl_certs:
                cmd.append("--ignore-ssl-certs")
            sh(*cmd, *args)
            m.add(cfg.node.version)

        for plugin in cfg.topo_plugins:
            plugin_module = cfg.loaded[plugin]
            for req in get_requires(plugin_module.defaults, "npm"):
                if not m.check(req):
                    sh(npm, "install", "-g", req)
                    m.add(req)


def create_npm_cmd(cfg: ConfigTree, node_dir: Path) -> None:
    """Writes an npm.cmd into the venv's Scripts directory which can be used to
    execute npm.cmd from another directory.

    """
    cmd = dedent(
        rf"""
        @echo off
        setlocal

        set NPM_EXEC={node_dir}\npm.cmd
        if not exist "%NPM_EXEC%" (
            echo Error: npm not found at %NPM_EXEC%
            exit /b 1
        )
        "%NPM_EXEC%" %*
        endlocal
    """
    )
    writetext(cfg.python.scriptdir / "npm.cmd", cmd)
