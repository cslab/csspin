# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, die, echo, info, interpolate1, memoizer, mkdir, rmtree, setenv

defaults = config(
    version=None,
    installdir="{spin.cache}/{platform.tag}",
    java_home=None,
)

N = os.path.normcase


def set_java_home(cfg):
    setenv(JAVA_HOME=N(cfg.java.java_home))
    setenv(
        N(f"set PATH=$JAVA_HOME/bin{os.pathsep}$PATH"),
        PATH=os.pathsep.join((N("{JAVA_HOME}/bin"), "{PATH}")),
    )


def check_java(cfg):
    mkdir("{java.installdir}")
    with memoizer("{java.installdir}/java.pickle") as m:
        version = None
        for version, java_home in m.items():
            if version == cfg.java.version:
                cfg.java.java_home = java_home
                set_java_home(cfg)
                return True
    return False


def provision(cfg):
    if check_java(cfg):
        return

    import jdk

    real_get_download_url = jdk.get_download_url

    def monkey_get_download_url(*args):
        url = real_get_download_url(*args)
        echo(f"Downloading JDK from {url}")
        return url

    jdk.get_download_url = monkey_get_download_url

    with memoizer("{java.installdir}/java.pickle") as m:
        # FIXME: in case there already is a JDK installation, but it
        # is not yet memoized, unpacking the freshly downloaded new
        # distribution into the same directory will fail, since the
        # JDK archives have r/o files. But we cannot remove the
        # installation directory beforehand, since we do not know it's
        # name: `java_home` is computed from the archive contents.
        try:
            java_home = jdk.install(
                cfg.java.version, path=interpolate1(cfg.java.installdir)
            )
        except PermissionError as ex:
            die(
                "Unpacking the JDK archive failed. There probably already is a JDK in"
                f" the same location, that you have to remove manually ({ex})."
            )
        m.add((cfg.java.version, java_home))
        cfg.java.java_home = java_home

    set_java_home(cfg)


def init(cfg):
    if not check_java(cfg):
        die(
            "JDK {java.version} is not yet provisioned.\n"
            "You might want to run spin with the --provision flag."
        )


def configure(cfg):
    if not cfg.java.version:
        die(
            "Spin's Java plugin no longer sets a default version.\n"
            "Please choose a version in spinfile.yaml by setting java.version"
        )
