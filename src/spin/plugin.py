import click
import inspect
from .cli import commands
from .util import (
    echo,
    cd,
    mkdir,
    die,
    sh,
    Command,
    exists,
    rmtree,
    config,
    namespaces,
    readbytes,
    writebytes,
    readtext,
    writetext,
    persist,
    unpersist,
    memoizer,
    get_tree,
    setenv,
)

__all__ = [
    "task",
    "group",
    "echo",
    "cd",
    "mkdir",
    "die",
    "sh",
    "Command",
    "exists",
    "rmtree",
    "config",
    "namespaces",
    "readbytes",
    "writebytes",
    "readtext",
    "writetext",
    "persist",
    "unpersist",
    "argument",
    "option",
    "memoizer",
    "invoke",
    "setenv",
]


def argument(**kwargs):
    def wrapper(param_name):
        return click.argument(param_name, **kwargs)

    return wrapper


def option(*args, **kwargs):
    def wrapper(param_name):
        return click.option(*args, **kwargs)

    return wrapper


def task(*args, **kwargs):
    def task_wrapper(fn, group=commands):
        task_object = fn
        context_settings = config()
        sig = inspect.signature(task_object)
        param_names = list(sig.parameters.keys())
        if param_names:
            if param_names[0] == "ctx":
                task_object = click.pass_context(fn)
                param_names.pop(0)
        for pn in param_names:
            if pn == "passthrough":
                context_settings.ignore_unknown_options = True
                context_settings.allow_extra_args = True
            param = sig.parameters[pn]
            task_object = param.annotation(pn)(task_object)
        task_object = group.command(context_settings=context_settings)(
            task_object
        )
        hook = kwargs.pop("when", None)
        if hook:
            cfg = get_tree()
            hook_tree = cfg.get("hooks", config())
            hooks = hook_tree.setdefault(hook, [])
            hooks.append(task_object)
        for alias in kwargs.pop("aliases", []):
            group.register_alias(alias, task_object)
        return task_object

    if args:
        # We have positional arguments, assume @task without
        # parentheses
        return task_wrapper(*args, **kwargs)

    # Else, assume @task(<options>)
    return task_wrapper


def group(fn):
    def subtask(fn):
        return task(fn, grp)

    grp = commands.group()(click.pass_context(fn))
    grp.task = subtask
    return grp


def invoke(hook):
    ctx = click.get_current_context()
    cfg = get_tree()
    for task_object in cfg.hooks.setdefault(hook, []):
        ctx.invoke(task_object)
