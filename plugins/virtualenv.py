from spin.plugin import (
    config,
    sh,
    exists,
    rmtree,
    persist,
    unpersist,
    group,
    echo,
)

requires = ["python"]

defaults = config(
    venv="{spin.project_root}/" "{virtualenv.abitag}-{python.platform}",
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
    cleanup(ctx)


def init(ctx):
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
    ctx.obj.virtualenv.abitag = cpi.stdout.decode().strip()

    if not exists("{virtualenv.command}"):
        sh("{python.pip} install virtualenv")
    if not exists("{virtualenv.venv}"):
        sh("{virtualenv.command} -p {python.interpreter} {virtualenv.venv}")

    if ctx.obj.requirements:
        installed_by_spin = unpersist("{virtualenv.venv}/spininfo.pickle", [])
        for req in ctx.obj.requirements:
            if req not in installed_by_spin:
                sh("{virtualenv.pip} install {req}")
                installed_by_spin.append(req)
        persist("{virtualenv.venv}/spininfo.pickle", installed_by_spin)


def cleanup(ctx):
    if exists("{virtualenv.venv}"):
        rmtree("{virtualenv.venv}")
