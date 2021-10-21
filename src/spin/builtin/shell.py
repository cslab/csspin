# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin import config, task

defaults = config(
    requires=config(python=["psutil"] if sys.platform.startswith("win32") else [])
)


@task()
def shell(cfg):
    if sys.platform.startswith("win32"):
        import subprocess

        import psutil

        # Call the activate scripts to set the Prompt
        SHELLS = {
            "cmd": ["/k", "activate.bat"],
            "powershell": ["-NoExit", "activate.ps1"],
            "pwsh": ["-NoExit", "activate.ps1"],
        }
        pid = os.getpid()
        python_process = psutil.Process(pid)
        # get parents and find the shell
        # use the reversed order to skip intermediate cmd scripts
        plist = python_process.parents()
        plist.reverse()

        for proc in plist:
            # name without extension
            name = proc.name().split(".")[0]
            if name in SHELLS:
                shell = proc.exe()
                subprocess.run([shell] + SHELLS[name])
                break
    else:
        os.execvp(os.environ["SHELL"], [os.environ["SHELL"], "-i"])
