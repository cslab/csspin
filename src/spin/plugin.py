import click
import inspect
from .cli import commands
from .util import (
    echo,
    cd,
    mkdir,
    die,
    sh,
    exists,
    rmtree,
    config,
    namespaces,
    readbytes,
    writebytes,
    persist,
    unpersist,
)

__all__ = [  # noqa
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
    "namespaces",
    "readbytes",
    "writebytes",
    "persist",
    "unpersist",
    "argument",
    "option",
]


def argument(**kwargs):
    def wrapper(param_name):
        return click.argument(param_name, **kwargs)
    return wrapper


def option(*args, **kwargs):
    def wrapper(param_name):
        return click.option(*args, **kwargs)
    return wrapper


def task(fn, group=commands):
    task_object = fn
    context_settings = config()
    sig = inspect.signature(task_object)
    param_names = list(sig.parameters.keys())
    if param_names[0] == "ctx":
        task_object = click.pass_context(fn)
        param_names.pop(0)
    for pn in param_names:
        param = sig.parameters[pn]
        task_object = param.annotation(pn)(task_object)
    return group.command(context_settings=context_settings)(task_object)


def group(fn):
    def subtask(fn):
        return task(fn, grp)

    grp = commands.group()(click.pass_context(fn))
    grp.task = subtask
    return grp
