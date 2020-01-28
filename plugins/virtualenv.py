from spin.plugin import (
    config,
    sh,
    exists,
    rmtree,
    memoizer,
    group,
    echo,
)

requires = ["python"]

defaults = config(
    venv="{spin.project_root}/{virtualenv.abitag}-{python.platform}",
    command="{python.bin_dir}/virtualenv",
    bindir="{virtualenv.venv}/bin",
    python="{virtualenv.bindir}/python",
    pip="{virtualenv.bindir}/pip",
)


@group
def venv(ctx):
    pass


@venv.task
def info(ctx):
    echo("{virtualenv.venv}")


@venv.task
def rm(ctx):
    cleanup(ctx.obj)


def init(cfg):
    # To get the ABI tag, we've to call into the target interpreter,
    # which is not the one running the spin program. Not super cool,
    # firing up the interpreter just for that is slow.
    cpi = sh(
        "{python.interpreter}",
        "-c",
        "from wheel.pep425tags import get_abi_tag; print(get_abi_tag())",
        capture_output=True,
        silent=True,
    )
    cfg.virtualenv.abitag = cpi.stdout.decode().strip()

    if not exists("{virtualenv.command}"):
        sh("{python.pip} install virtualenv")
    if not exists("{virtualenv.venv}"):
        sh("{virtualenv.command} -p {python.interpreter} {virtualenv.venv}")

    with memoizer("{virtualenv.venv}/spininfo.memo") as m:
        for req in cfg.requirements:
            if not m.check(req):
                sh("{virtualenv.pip} install {req}")
                m.add(req)


def cleanup(cfg):
    if exists("{virtualenv.venv}"):
        rmtree("{virtualenv.venv}")
