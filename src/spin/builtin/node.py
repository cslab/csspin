# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin import config, die, get_requires, memoizer, sh

defaults = config(
    version=None,
    mirror=None,
    ignore_ssl_certs=False,
    jobs=os.cpu_count(),
    requires=config(
        spin=[".python"],
        python=["nodeenv"],
        npm=["sass"],
    ),
    memo="{python.venv}/nodeversions.memo",
)


def configure(cfg):
    if cfg.node.version is None:
        die(
            "Spin's Node.js plugin does not set a default version.\n"
            "Please choose a version in spinfile.yaml by setting node.version"
        )


def provision(cfg):
    with memoizer(cfg.node.memo) as m:
        if cfg.node.version in ("latest", "lts") or not m.check(cfg.node.version):
            cmd = [
                cfg.python.python,
                "-mnodeenv",
                "--python-virtualenv",
                f"--jobs={cfg.node.jobs}",
                f"--node={cfg.node.version}",
                "--with-npm",
            ]
            if cfg.node.mirror:
                cmd.append(f"--mirror={cfg.node.mirror}")
            if cfg.node.ignore_ssl_certs:
                cmd.append("--ignore-ssl-certs")
            sh(*cmd)
            m.add(cfg.node.version)

        for plugin in cfg.topo_plugins:
            plugin_module = cfg.loaded[plugin]
            for req in get_requires(plugin_module.defaults, "npm"):
                if not m.check(req):
                    npm = os.path.join(cfg.python.scriptdir, "npm")
                    if sys.platform == "win32":
                        npm += ".cmd"
                    sh(npm, "install", "-g", req)
                    m.add(req)
