from spin import config, echo, task

defaults = config(foo="bar")


@task()
def dummy(cfg):
    echo("This is spin's dummy plugin")
