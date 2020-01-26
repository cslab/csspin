from spin.plugin import *
from wheel import pep425tags
import os


defaults = config(
    pyenv=config(
        url="https://github.com/pyenv/pyenv.git",
        path="{spin.userprofile}/pyenv",
        python_build="{python.pyenv.path}/plugins/python-build/bin/python-build",
    ),
    platform="{pep425tags.get_platform()}",
    version="3.8.1",
    inst_dir="{spin.userprofile}/{python.platform}/python/{python.version}",
    bin_dir="{python.inst_dir}/bin",
    python="{python.bin_dir}/python",
    pip="{python.bin_dir}/pip",
)


@task
def python(ctx):
    sh("{python.python}", "--version")


def init(ctx):
    if not exists("{python.python}"):
        echo("Installing to {python.inst_dir}")
        if not exists("{python.pyenv.path}"):
            sh("git clone {python.pyenv.url} {python.pyenv.path}")
        sh("{python.pyenv.python_build} {python.version} {python.inst_dir}")
        # Upgrade pip
        sh("{python.python} -m pip install --upgrade pip")


def cleanup(ctx):
    if exists("{python.inst_dir}"):
        rmtree("{python.inst_dir}")
