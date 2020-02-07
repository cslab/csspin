import os

from .api import echo, sh


class BaseExecutor(object):
    def __init__(self, name, definition):
        self.banner = getattr(definition, "banner", "")

    def run(self, cmd):
        if self.banner:
            echo(self.banner)


# Docker is relatively straightforward: run the command in the
# container.
class DockerExecutor(BaseExecutor):
    def __init__(self, name, definition):
        super().__init__(name, definition)
        cmd = ["docker"]

        context = getattr(definition, "context", "")
        if context:
            cmd += ["-c", context]
        cmd += ["run", "--rm"]
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
        super().run(cmd)
        cmd = self._docker + cmd
        sh(*cmd)


class HostExecutor(BaseExecutor):
    """Run command on this host."""

    def run(self, cmd):
        super().run(cmd)
        self.ctx.run(cmd, pty=True)
