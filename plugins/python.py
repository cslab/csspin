from spin.plugin import config, task, sh, echo, exists, rmtree, namespaces
from wheel import pep425tags


defaults = config(
    pyenv=config(
        url="https://github.com/pyenv/pyenv.git",
        path="{spin.userprofile}/pyenv",
        python_build=(
            "{python.pyenv.path}/plugins/python-build/bin/python-build"
        ),
    ),
    platform=pep425tags.get_platform(),
    version="3.8.1",
    inst_dir="{spin.userprofile}/{python.platform}/python/{python.version}",
    bin_dir="{python.inst_dir}/bin",
    interpreter="{python.bin_dir}/python",
    pip="{python.bin_dir}/pip",
    use_existing=False,
)


@task
def python(ctx):
    sh("{python.interpreter}", "--version")


def init(ctx):
    if not ctx.obj.python.use_existing:
        with namespaces(ctx.obj.python):
            if not exists("{interpreter}"):
                echo("Installing Python {version} to {inst_dir}")
                if not exists("{pyenv.path}"):
                    sh("git clone {pyenv.url} {pyenv.path}")
                sh("{pyenv.python_build} {version} {inst_dir}")
                sh("{interpreter} -m pip install --upgrade pip")
                sh("{pip} install wheel")


def cleanup(ctx):
    if not ctx.obj.python.use_existing:
        if exists("{python.inst_dir}"):
            rmtree("{python.inst_dir}")
