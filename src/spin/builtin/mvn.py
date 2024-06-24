# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import os
import random
import sys
import tarfile
import urllib

from spin import config, exists, info, interpolate1, option, setenv, sh, task, warn

defaults = config(
    exe="mvn",
    goals=[],
    opts=[],
    defines={},
    pom_file="pom.xml",
    requires=config(spin=["spin.builtin.java"]),
    packages=[],
    version="3.8.3",
    mirrors=[
        "https://ftp.fau.de/apache/",
        "https://dlcdn.apache.org/",
    ],
    url="maven/maven-3/{mvn.version}/binaries/apache-maven-{mvn.version}-bin.tar.gz",
    mavendir="{spin.cache}/apache-maven-{mvn.version}",
)


def provision(cfg):
    if not exists(cfg.mvn.mavendir):
        random.shuffle(cfg.mvn.mirrors)
        for mirror in cfg.mvn.mirrors:
            url = interpolate1(mirror + cfg.mvn.url)
            info(f"Downloading {url}")
            try:
                filename, _ = urllib.request.urlretrieve(url)
            except urllib.error.HTTPError as e:
                # maven removes old version from the mirrors...
                if e.status == 404:
                    warn(
                        f"Maven {cfg.mvn.version} not found in the mirrors... "
                        f"Trying to retrieve version {cfg.mvn.version} from archive."
                    )
                    mirror = "https://archive.apache.org/dist/"
                    url = interpolate1(mirror + cfg.mvn.url)
                    filename, _ = urllib.request.urlretrieve(url)
                else:
                    raise
            except urllib.error.URLError:
                warn(f"Mirror {mirror} currently not reachable...")
                continue
            break
        else:
            raise Exception(  # pylint: disable=broad-exception-raised
                "Currently no mirror reachable"
            )
        with tarfile.open(filename, "r:gz") as tar:
            tar.extractall(os.path.dirname(interpolate1(cfg.mvn.mavendir)))
    init(cfg)


def init(cfg):
    bindir = os.path.normpath(interpolate1(f"{cfg.mvn.mavendir}/bin"))
    setenv(
        f"set PATH={bindir}{os.pathsep}$PATH",
        PATH=os.pathsep.join((f"{bindir}", "{PATH}")),
    )


@task(when="build")
def mvn(
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
    cmd = "{mvn.exe}"
    if sys.platform.startswith("win32"):
        cmd += ".cmd"
    opts = cfg.mvn.opts
    if not cfg.verbose:
        opts.append("-q")
    # add pom file
    opts.append("-f")
    opts.append(pom_file or cfg.mvn.pom_file)

    # add defines
    cfg_defines = cfg.mvn.defines
    for d in defines:
        name, val = d.split("=")
        cfg_defines[name] = val

    for d in cfg_defines.items():
        opts.append(f"-D{d[0]}={d[1]}")

    # do not use goals when some extra args are used
    if not args:
        opts.extend(cfg.mvn.goals)
    sh(cmd, *opts, *args)
