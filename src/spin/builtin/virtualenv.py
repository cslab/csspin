# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import logging
import os
import shutil
import sys

from spin import (
    EXPORTS,
    Command,
    config,
    echo,
    exists,
    group,
    interpolate1,
    memoizer,
    readtext,
    rmtree,
    sh,
    writetext,
)

N = os.path.normcase


defaults = config(
    venv=N("{spin.project_root}/{virtualenv.abitag}-{platform.tag}"),
    memo=N("{virtualenv.venv}/spininfo.memo"),
    bindir=(
        N("{virtualenv.venv}/bin") if sys.platform != "win32" else "{virtualenv.venv}"
    ),
    scriptdir=(
        N("{virtualenv.venv}/bin")
        if sys.platform != "win32"
        else N("{virtualenv.venv}/Scripts")
    ),
    python=N("{virtualenv.bindir}/python"),
    requires=[".python"],
    pipconf=config(),
    abitag="unprovisioned",
    activated=False,
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


def get_abi_tag(cfg):
    # To get the ABI tag, we've to call into the target interpreter,
    # which is not the one running the spin program. Not super cool,
    # firing up the interpreter just for that is slow.
    # ABI detection has been moved to file which is then called by the interpreter.
    from spin import get_abi_tag

    abitag = (
        sh(
            "{python.interpreter}",
            get_abi_tag.__file__,
            capture_output=True,
            silent=not cfg.verbose,
        )
        .stdout.decode()
        .strip()
    )
    return abitag


def configure(cfg):
    if (
        cfg.python.use or exists("{python.interpreter}")
    ) and cfg.virtualenv.abitag == "unprovisioned":
        cfg.virtualenv.abitag = get_abi_tag(cfg)


def init(cfg):
    configure(cfg)
    if not cfg.virtualenv.activated:
        activate_this = interpolate1("{virtualenv.scriptdir}/activate_this.py")
        echo("Activating {virtualenv.venv}")
        exec(open(activate_this).read(), {"__file__": activate_this})
        cfg.virtualenv.activated = True


def create_dotenv(schema):
    if exists(schema.activatescript):
        setters = []
        resetters = []
        for name, value in EXPORTS.items():
            if value:
                setters.append(schema.setpattern.format(name=name, value=value))
                resetters.append(schema.resetpattern.format(name=name, value=value))
        resetters = "\n".join(resetters)
        setters = "\n".join(setters)
        activate = readtext(schema.activatescript)
        if schema.patchmarker not in activate:
            echo(f"Patching {schema.activatescript}")
            shutil.copyfile(
                interpolate1(f"{schema.activatescript}"),
                interpolate1(f"{schema.activatescript}.bak"),
            )
        activate = readtext(f"{schema.activatescript}.bak")
        newscript = schema.script.format(
            patchmarker=schema.patchmarker,
            original=activate.replace("deactivate", "origdeactivate"),
            resetters=resetters,
            setters=setters,
        )
        writetext(f"{schema.activatescript}", newscript)


class EnvBash:
    patchmarker = "\n## PATCHED BY spin.builtin.virtualenv\n"
    spinenv = "{virtualenv.venv}/.spinenv"
    activatescript = "{virtualenv.scriptdir}/activate"
    setpattern = """
_OLD_SPIN_{name}="${name}"
{name}="{value}"
export {name}
"""
    resetpattern = """
    if ! [ -z "${{_OLD_SPIN_{name}+_}}" ] ; then
        {name}="$_OLD_SPIN_{name}"
        export {name}
        unset _OLD_SPIN_{name}
    fi
"""
    script = """
{patchmarker}
{original}
deactivate () {{
    {resetters}
    if [ ! "${{1-}}" = "nondestructive" ] ; then
        # Self destruct!
        unset -f deactivate
        origdeactivate
    fi
}}

deactivate nondestructive

{setters}

# The hash command must be called to get it to forget past
# commands. Without forgetting past commands the $PATH changes
# we made may not be respected
hash -r 2>/dev/null

"""


def finalize_provision(cfg):
    create_dotenv(EnvBash)
    #     ".spinenv",
    #     'export {name}="{value}"',
    #     "activate",
    #     ". $VIRTUAL_ENV/.spinenv",
    # )
    # create_dotenv(
    #     ".spinenv.csh",
    #     'setenv {name} "{value}"',
    #     "activate.csh",
    #     "source $VIRTUAL_ENV/.spinenv.csh",
    # )
    # create_dotenv(
    #     ".spinenv.ps1",
    #     '$env:{name} = "{value}"',
    #     "activate.ps1",
    #     '. "$VIRTUAL_ENV/.spinenv.ps1"',
    # )
    # create_dotenv(
    #     ".spinenv.bat",
    #     'set {name}="{value}"',
    #     "activate.bat",
    #     'call "$VIRTUAL_ENV/.spinenv.bat"',
    # )


def provision(cfg):
    configure(cfg)
    if not cfg.python.use and not exists(
        "{python.script_dir}/virtualenv{platform.exe}"
    ):
        # If we use Python provisioned by spin, add virtualenv if
        # necessary.
        sh("{python.interpreter} -m pip -q install virtualenv")

    cmd = ["{python.interpreter}", "-m", "virtualenv"]
    if not cfg.verbose:
        cmd.append("-q")
    virtualenv = Command(*cmd)

    if not exists("{virtualenv.venv}"):
        # download seeds since pip is too old in manylinux
        virtualenv("-p", "{python.interpreter}", "{virtualenv.venv}", "--download")

    # This sets PATH to the venv
    init(cfg)

    # Update the pip in the venv
    sh("python -m pip -q install -U pip")

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
        pipconf = "{virtualenv.venv}/pip.ini"
    else:
        pipconf = "{virtualenv.venv}/pip.conf"

    if not exists(pipconf):
        writetext(pipconf, "\n".join(text))

    with memoizer("{virtualenv.memo}") as m:

        replacements = cfg.get("devpackages", {})

        def pipit(req):
            req = replacements.get(req, req)
            if not m.check(req):
                pip("install", *req.split())
                m.add(req)
            elif cfg.verbose:
                echo(f"{req} already installed!")

        # Plugins can define a 'venv_hook' function, to give them a
        # chance to do something with the virtual environment just
        # being provisioned (e.g. preparing the venv by adding pth
        # files or by adding packages with other installers like
        # easy_install).
        for plugin in cfg.topo_plugins:
            plugin_module = cfg.loaded[plugin]
            hook = getattr(plugin_module, "venv_hook", None)
            if hook is not None:
                logging.info(f"{plugin_module.__name__}.venv_hook()")
                hook(cfg)

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
