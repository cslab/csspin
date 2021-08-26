# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""Run spin commands elsewhere, e.g. in a Docker container."""

import os
import sys

from . import echo, sh, tree


def spin_is_editable():
    editable = None
    for path_item in sys.path:
        egg_link = os.path.join(path_item, "spin.egg-link")
        if os.path.isfile(egg_link):
            with open(egg_link) as f:
                editable = os.path.normpath(
                    os.path.join(*[line.strip() for line in f.readlines()])
                )
    return editable


def build_cruises(cfg):
    for key in cfg.cruise.keys():
        if not key.startswith("@"):
            cruise = cfg.cruise[key]
            tree.tree_update_key(cruise, "tags", cruise.tags.split())
            for tag in ["@" + tag for tag in cruise.tags]:
                if tag in cfg.cruise:
                    tree.tree_merge(cruise, cfg.cruise[tag])


def match_cruises(cfg, selectors):
    for name, definition in cfg.cruise.items():
        if name.startswith("@"):
            continue
        elif "@all" in selectors:
            yield name, definition
        if name in selectors:
            yield name, definition
        elif any(("@" + tag in selectors) for tag in getattr(definition, "tags", [])):
            yield name, definition


def do_cruise(cfg, cruiseopt, interactive):
    spin_args = sys.argv[1:]
    while spin_args[0] in ("-c", "--cruise", "-C", "--change-directory"):
        spin_args.pop(0)
        spin_args.pop(0)
    for name, definition in match_cruises(cfg, cruiseopt):
        cmd = [getattr(definition, "cruise_spin", cfg.spin.cruise_spin)] + getattr(
            definition, "opts", []
        )
        for pname, pvalue in getattr(definition, "properties", {}).items():
            cmd += ["-p", f"{pname}={pvalue}"]
        cmd += spin_args
        if len(spin_args) == 0:
            # interactivly run a docker container having spin installed
            interactive = True
            cmd = ["bash", "-c", " ".join(cmd + [";", "bash"])]
        executor = definition.executor(name, definition, interactive)
        executor.run(cmd)


class BaseExecutor:
    """Base class for executors."""

    def __init__(self, name, definition, interactive):
        """Set up executor from definition."""
        self.name = name
        self.definition = definition
        self.interactive = interactive
        self.banner = getattr(definition, "banner", "")

    def run(self, cmd):
        """Run 'cmd' using the executor."""
        if self.banner:
            echo(self.banner)


# Docker is straightforward: run the command in the container.
class DockerExecutor(BaseExecutor):
    """Execute commands in Docker containers."""

    def __init__(self, name, definition, interactive):
        """Set up docker command line."""
        super().__init__(name, definition, interactive)
        cmd = ["docker"]

        context = getattr(definition, "context", "")
        if context:
            cmd += ["-c", context]
        cmd += ["run", "--rm"]
        if interactive:
            cmd += ["-it"]
        env = getattr(definition, "env", {})
        for key, value in env.items():
            cmd += ["-e", f"{key}={value}"]

        volprefix = getattr(definition, "volprefix", "")
        home = os.path.expanduser("~")
        cmd += ["-v", f"{volprefix}{home}:{volprefix}{home}"]
        if "windows" in getattr(definition, "tags", []):
            cmd += ["-e", f"USERPROFILE={volprefix}{home}"]
        else:
            cmd += ["-e", f"HOME={volprefix}{home}"]
            # FIXME: docker writes files which are owned by root to the .local dir...
            # This causes some problems.
            cmd += ["-v", f"{volprefix}{home}/.local"]

        devspin = spin_is_editable()
        if devspin:
            cmd += ["-e", f"SPIN_SANDBOX={volprefix}{devspin}"]

        workdir = os.getcwd()
        cmd += ["-w", f"{volprefix}{workdir}"]
        cmd += [definition.image]
        self._docker = cmd

    def run(self, cmd):
        """Run 'cmd' in Docker container."""
        super().run(cmd)
        cmd = self._docker + cmd
        sh(*cmd)


class HostExecutor(BaseExecutor):
    """Run command on this host."""

    def run(self, cmd):
        """Run command locally."""
        super().run(cmd)
        sh(*cmd)
