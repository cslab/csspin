# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""Grab explicitly defined tasks from the configuration tree and add
them as subcommands."""

from spin import sh, task


class TaskDefinition:
    def __init__(self, definition):
        self._definition = definition

    def __call__(self):
        env = self._definition.get("env", None)
        for cmd in self._definition.get("script", []):
            sh(cmd, env=env)


def configure(cfg):
    for task_name, task_definition in cfg.get("extra-tasks", {}).items():
        task(task_name)(TaskDefinition(task_definition))
