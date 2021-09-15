# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""Grab explicitly defined tasks from the configuration tree and add
them as subcommands."""

from spin import run_script, run_spin, sh, task


class TaskDefinition:
    def __init__(self, definition):
        self._definition = definition

    def __call__(self):
        env = self._definition.get("env", None)
        run_script(self._definition.get("script", []), env)
        run_spin(self._definition.get("spin", []))


def configure(cfg):
    for task_name, task_definition in cfg.get("extra-tasks", {}).items():
        help = task_definition.get("help", "")
        task(task_name, help=help)(TaskDefinition(task_definition))
