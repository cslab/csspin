from spin import echo, task


@task()
def demo(cfg):
    echo("This is spin's demo plugin")
