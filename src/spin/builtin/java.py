# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, echo, group, memoizer, rmtree, setenv

defaults = config(
    version="16",
)


@group()
def java(cfg):
    """Manage JDK installation"""
    pass


def init(cfg):
    import jdk

    real_get_downoad_url = jdk.get_download_url

    def monkey_get_download_url(*args):
        url = real_get_downoad_url(*args)
        echo(f"Downloading JDK from {url}")
        return url

    jdk.get_download_url = monkey_get_download_url

    java_home = None
    with memoizer(f"{jdk._JDK_DIR}/versions.pickle") as m:
        version = None
        for version, java_home in m.items():
            if version == cfg.java.version:
                break
        if version != cfg.java.version:
            java_home = jdk.install(cfg.java.version)
            m.add((cfg.java.version, java_home))
        setenv(JAVA_HOME=java_home)
        setenv(
            f"set PATH=$JAVA_HOME/bin{os.pathsep}$PATH",
            PATH="{JAVA_HOME}/bin:{PATH}",
        )


@java.task(aliases=["remove"])
def rm(cfg):
    import jdk

    with memoizer(f"{jdk._JDK_DIR}/versions.pickle") as m:
        for version, java_home in m.items():
            rmtree(java_home)
        m.clear()
