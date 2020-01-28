from spin.plugin import config, sh, task, argument

defaults = config()

requires = ["virtualenv"]


@task
def flake8(ctx, files: argument(nargs=-1)):
    """Run flake8 to lint Python code."""
    if not files:
        files = (
            "{spin.project_root}/src",
            "{spin.project_root}/plugins",
        )

    sh("{virtualenv.bindir}/flake8", *files)


def configure(ctx):
    ctx.obj.requirements.append("flake8")
