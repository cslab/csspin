# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""Run spin commands elsewhere, e.g. in a Docker container."""
import os

from .api import echo, sh


class BaseExecutor:
    """Base class for executors."""

    def __init__(self, name, definition):
        """Set up executor from definition."""
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
        super().__init__(name, definition)
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
        self.ctx.run(cmd, pty=True)
