from spin.plugin import config, task, sh, setenv, echo, exists, readtext, get_tree, argument
from spin.util import interpolate1
import yaml
import os

defaults = config(formats=["bdist_wheel"], devpi="{virtualenv.bindir}/devpi",)
requires = [".virtualenv"]
packages = ["devpi-client", "keyring"]


def prepare_environment():
    setenv(
        DEVPI_VENV="{virtualenv.venv}", DEVPI_CLIENTDIR="{spin.spin_dir}/devpi"
    )


@task
def stage():
    prepare_environment()
    data = {}
    if exists("{spin.spin_dir}/devpi/current.json"):
        data = yaml.safe_load(readtext("{spin.spin_dir}/devpi/current.json"))
    if data.get("index", "") != interpolate1("{devpi.stage}"):
        sh("{devpi.devpi} use -t yes {devpi.stage}")
    sh("{devpi.devpi} login {devpi.user}")
    python = os.path.abspath(get_tree().virtualenv.python)
    sh("{devpi.devpi} upload -p %s --no-vcs --formats={','.join(devpi.formats)}" % python)


@task
def devpi(passthrough: argument(nargs=-1)):
    sh("{devpi.devpi}", *passthrough)
