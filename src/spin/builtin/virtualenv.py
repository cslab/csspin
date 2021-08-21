# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os
import sys

from spin import (
    Command,
    config,
    echo,
    exists,
    group,
    interpolate1,
    memoizer,
    rmtree,
    setenv,
    sh,
    writetext,
)


defaults = config(
    venv="{spin.project_root}/{virtualenv.abitag}-{python.platform}",
    memo="{virtualenv.venv}/spininfo.memo",
    bindir=(
        "{virtualenv.venv}/bin" if sys.platform != "win32" else "{virtualenv.venv}"
    ),
    scriptdir=(
        "{virtualenv.venv}/bin"
        if sys.platform != "win32"
        else "{virtualenv.venv}/Scripts"
    ),
    python="{virtualenv.bindir}/python",
    requires=[".python"],
    pipconf=config(),
)


@group()
def venv(ctx):
    """Manage the project's virtual environment."""
    pass


@venv.task()
def info(ctx):
    echo("{virtualenv.venv}")


@venv.task()
def rm(cfg):
    cleanup(cfg)


def get_abi_tag():
    # To get the ABI tag, we've to call into the target interpreter,
    # which is not the one running the spin program. Not super cool,
    # firing up the interpreter just for that is slow.
    # ABI detection has been moved to file which is then called by the interpreter.
    from spin import get_abi_tag

    return (
        sh(
            "{python.interpreter}",
            get_abi_tag.__file__,
            capture_output=True,
            silent=False,
        )
        .stdout.decode()
        .strip()
    )


def init(cfg):
    cfg.virtualenv.abitag = get_abi_tag()

    if not cfg.python.use and not exists(
        "{python.script_dir}/virtualenv{platform.exe}"
    ):
        # If we use Python provisioned by spin, add virtualenv if
        # necessary.
        sh("{python.interpreter} -m pip install virtualenv==20.0.23")

    cmd = ["{python.interpreter}", "-m", "virtualenv"]
    if not cfg.verbose:
        cmd.append("-q")
    virtualenv = Command(*cmd)

    if not exists("{virtualenv.venv}"):
        # download seeds since pip is too old in manylinux
        virtualenv("-p", "{python.interpreter}", "{virtualenv.venv}", "--download")

    # It is more useful to abspath virtualenv bindir before pushing it
    # onto the PATH, as anything run from a different directory will
    # not pick up the venv bin.
    if sys.platform == "win32":
        venvabs = os.pathsep.join(
            (
                os.path.abspath(interpolate1("{virtualenv.bindir}")),
                os.path.abspath(interpolate1("{virtualenv.scriptdir}")),
            )
        )
    else:
        venvabs = os.path.abspath(interpolate1("{virtualenv.bindir}"))
    setenv(
        f"set PATH={venvabs}{os.pathsep}$PATH",
        PATH=os.pathsep.join((f"{venvabs}", os.environ["PATH"])),
    )
    cmd = ["pip"]
    if not cfg.verbose:
        cmd.append("-q")
    pip = Command(*cmd)

    # This is a much faster alternative to calling pip config
    # below; we leave it active here for now, enjoying a faster
    # spin until we better understand the drawbacks.
    text = []
    for section, settings in cfg.virtualenv.pipconf.items():
        text.append(f"[{section}]")
        for key, value in settings.items():
            text.append(f"{key} = {interpolate1(value)}")
    if sys.platform == "win32":
        pipconf = "pip.ini"
    else:
        pipconf = "pip.conf"

    writetext("{virtualenv.venv}/" + pipconf, "\n".join(text))

    with memoizer("{virtualenv.memo}") as m:

        replacements = cfg.get("devpackages", {})

        def pipit(req):
            req = replacements.get(req, req)
            if not m.check(req):
                pip("install", *req.split())
                m.add(req)

        # The provision-hooks have to run before installing the other
        # plugins. Otherwise the virtualenv may be only partially
        # working and the latter may fail.
        for plugin in cfg.topo_plugins:
            plugin_module = cfg.loaded[plugin]
            provision_hook = getattr(plugin_module, "provision", None)
            if provision_hook is not None:
                provision_hook(cfg)

        # Install packages required by the project ('requirements')
        for req in cfg.requirements:
            pipit(req)

        # Install packages required by plugins used
        # ('<plugin>.packages')
        for plugin in cfg.topo_plugins:
            plugin_module = cfg.loaded[plugin]
            for req in plugin_module.defaults.get("packages", []):
                pipit(req)

        # If there is a setup.py, make an editable install (which
        # transitively also installs runtime dependencies of the
        # project).  FIXME: filename/location of setup.py should
        # probably be configurable
        if exists("setup.py"):
            pipit("-e .")


def cleanup(cfg):
    if exists("{virtualenv.venv}"):
        rmtree("{virtualenv.venv}")
