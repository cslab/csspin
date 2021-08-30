# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import random
import sys
import tarfile
import urllib

from spin import config, echo, exists, interpolate1, option, setenv, sh, task

defaults = config(
    cmd="mvn",
    goals=[],
    opts=[],
    defines={},
    pom_file="pom.xml",
    requires=[".java"],
    packages=[],
    version="3.8.2",
    mirrors=[
        "http://ftp.fau.de/apache/",
        "http://dlcdn.apache.org/",
        "http://apache.mirror.digionline.de/",
    ],
    url=(
        "maven/maven-3/{maven.version}/binaries/apache-maven-{maven.version}-bin.tar.gz"
    ),
    mavendir="{spin.userprofile}/apache-maven-{maven.version}",
)


def provision(cfg):
    if not exists(cfg.maven.mavendir):
        mirror = random.choice(cfg.maven.mirrors)
        url = interpolate1(mirror + cfg.maven.url)
        echo(f"Downloading {url}")
        filename, headers = urllib.request.urlretrieve(url)
        with tarfile.open(filename, "r:gz") as tar:
            tar.extractall(os.path.dirname(interpolate1(cfg.maven.mavendir)))
    init(cfg)


def init(cfg):
    bindir = os.path.normpath(interpolate1(cfg.maven.mavendir + "/bin"))
    setenv(
        f"set PATH={bindir}{os.pathsep}$PATH",
        PATH=os.pathsep.join((f"{bindir}", "{PATH}")),
    )


@task(when="build")
def maven(
    cfg,
    pom_file: option(
        "-f",
        "--file",
        "pom_file",
        show_default=(
            "Force the use of an alternate POM file "  # noqa
            "(or directory with pom.xml)"
        ),
    ),
    defines: option(
        "-D",
        "--define",
        "defines",
        multiple=True,
        show_default="Define a system property",  # noqa
    ),
    args,
):
    """Run maven command"""
    cmd = "{maven.cmd}"
    if sys.platform.startswith("win32"):
        cmd += ".cmd"
    opts = cfg.maven.opts
    if cfg.quiet:
        opts.append("-q")
    # add pom file
    opts.append("-f")
    opts.append(pom_file or cfg.maven.pom_file)

    # add defines
    cfg_defines = cfg.maven.defines
    for d in defines:
        name, val = d.split("=")
        cfg_defines[name] = val

    for d in cfg_defines.items():
        opts.append("-D{}={}".format(*d))

    # do not use goals when some extra args are used
    if not args:
        opts.extend(cfg.maven.goals)
    sh(cmd, *opts, *args, env=os.environ)
