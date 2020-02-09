# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""Run spin commands elsewhere, e.g. in a Docker container."""

import os
import sys

from .api import echo, merge_config, sh


def build_cruises(cfg):
    for key in cfg.cruise.keys():
        if not key.startswith("@"):
            cruise = cfg.cruise[key]
            cruise.tags = cruise.tags.split()
            for tag in ["@" + tag for tag in cruise.tags]:
                if tag in cfg.cruise:
                    merge_config(cruise, cfg.cruise[tag])


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


def do_cruise(cfg, cruiseopt, interactive):
    spin_args = []
    spin_base_opts = True
    i = 1
    while i < len(sys.argv):
        if spin_base_opts and sys.argv[i] in ("-c", "--cruise"):
            i += 1
        else:
            spin_args.append(sys.argv[i])
        if not sys.argv[i].startswith("-"):
            spin_base_opts = False
        i += 1
    for name, definition in match_cruises(cfg, cruiseopt):
        executor = definition.executor(name, definition, interactive)
        cmd = ["spin"] + getattr(definition, "opts", []) + spin_args
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
