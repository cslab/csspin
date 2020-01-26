from spin.plugin import config, sh, task

defaults = config()

requires=["virtualenv"]


@task
def flake8(ctx):
    sh("flake8", "{spin.project_root}/src")


def configure(ctx):
    ctx.obj.requirements.append("flake8")
