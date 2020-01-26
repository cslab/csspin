from spin.plugin import *
import os
from wheel import pep425tags

requires=["python"]

defaults = config(
    venv=
    "{spin.project_root}/"
    "{pep425tags.get_abi_tag()}-{pep425tags.get_platform()}",
    command="{python.bin_dir}/virtualenv",
)



def create(ctx):
    if not exists(defaults.venv_path):
        sh("virtualenv", "-p", "{config.python}", "{venv_path}")
        pip = os.path.join(ctx.obj.plugins.virtualenv.venv_location(ctx), "bin", "pip")
        if ctx.obj.requirements:
            sh(pip, "install", "-q", " ".join(ctx.obj.requirements))


def init(ctx):
    if not exists("{virtualenv.command}"):
        sh("{python.pip} install virtualenv")
    if not exists("{virtualenv.venv}"):
        sh("{virtualenv.command} -p {python.python} {virtualenv.venv}")


def cleanup(ctx):
    if exists("{virtualenv.venv}"):
        rmtree("{virtualenv.venv}")
