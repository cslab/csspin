# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin import echo, interpolate1, option, task


@task()
def cache(cfg, remove: option("--rm", "remove", is_flag=True)):
    if sys.platform == "win32":
        caches = {
            "compiler": os.path.join(interpolate1(cfg.python.venv), "compiler.pickle"),
            "msvc": os.path.join(os.environ["USERPROFILE"], ".scons_msvc_cache"),
        }
        echo(f"{'removing' if remove else 'showing'} caches...")

        for name, path in caches.items():
            msg = f"{name} cache: "
            if not os.path.exists(path):
                path = None
            msg += path or "not found"
            if remove and path:
                os.remove(path)
                msg += " ... removed"
            echo(msg)
    else:
        echo("no caches on this distro")
