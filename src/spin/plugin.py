import click
from .cli import commands
from .util import * # noqa

__all__ = [ # noqa
    "task",
    "group",
    "echo",
    "cd",
    "mkdir",
    "die",
    "sh",
    "exists",
    "rmtree",
    "config",
]


def task(fn, group=commands):
    task_object = group.command()(click.pass_context(fn))
    return task_object


def group(fn):
    def subtask(fn):
        return task(fn, grp)

    grp = commands.group()(click.pass_context(fn))
    grp.task = subtask
    return grp
