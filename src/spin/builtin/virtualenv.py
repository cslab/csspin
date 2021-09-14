# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""

``virtualenv``
==============

TBD

"""

import logging
import os
import shutil
import sys

from spin import (
    EXPORTS,
    Command,
    backtick,
    config,
    die,
    echo,
    exists,
    info,
    interpolate,
    interpolate1,
    memoizer,
    readtext,
    rmtree,
    sh,
    task,
    writetext,
)

N = os.path.normcase


defaults = config(
    venv=N("{spin.env_base}/{virtualenv.abitag}-{platform.tag}"),
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
    abitag=None,
)


def get_abi_tag(cfg):
    # To get the ABI tag, we've to call into the target interpreter,
    # which is not the one running the spin program. Not super cool,
    # firing up the interpreter just for that is slow.  ABI detection
    # has been moved to file which is then called by the interpreter.
    if not cfg.virtualenv.abitag:
        from spin import get_abi_tag

        abitag = backtick(
            "{python.interpreter}",
            get_abi_tag.__file__,
        )
        cfg.virtualenv.abitag = abitag.strip()


def init(cfg):
    get_abi_tag(cfg)
    if os.environ.get("VIRTUAL_ENV", "") != cfg.virtualenv.venv:
        activate_this = interpolate1("{virtualenv.scriptdir}/activate_this.py")
        if not exists(activate_this):
            die(
                "{virtualenv.venv} does not exist. You may want to provision it using"
                " spin --provision"
            )
        echo("activate {virtualenv.venv}")
        exec(open(activate_this).read(), {"__file__": activate_this})


@task()
def shell(cfg):
    part1 = os.path.basename(interpolate1("{spin.project_root}"))
    part2 = interpolate1("{virtualenv.abitag}")
    os.environ["PS1"] = f"({part1}:{part2}) " + os.environ["PS1"]
    os.execvp(os.environ["SHELL"], [os.environ["SHELL"], "--norc", "-i"])


def patch_activate(schema):
    if exists(schema.activatescript):
        setters = []
        resetters = []
        for name, value in EXPORTS.items():
            if value:
                setters.append(schema.setpattern.format(name=name, value=value))
                resetters.append(schema.resetpattern.format(name=name, value=value))
        resetters = "\n".join(resetters)
        setters = "\n".join(setters)
        original = readtext(schema.activatescript)
        if schema.patchmarker not in original:
            shutil.copyfile(
                interpolate1(f"{schema.activatescript}"),
                interpolate1(f"{schema.activatescript}.bak"),
            )
        info(f"Patching {schema.activatescript}")
        original = readtext(f"{schema.activatescript}.bak")
        for repl in schema.replacements:
            original = original.replace(repl[0], repl[1])
        newscript = schema.script.format(
            patchmarker=schema.patchmarker,
            original=original,
            resetters=resetters,
            setters=setters,
        )
        writetext(f"{schema.activatescript}", newscript)


class BashActivate:
    patchmarker = "\n## PATCHED BY spin.builtin.virtualenv\n"
    activatescript = "{virtualenv.scriptdir}/activate"
    replacements = [
        ("deactivate", "origdeactivate"),
    ]
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


class PowershellActivate:
    patchmarker = "\n## PATCHED BY spin.builtin.virtualenv\n"
    activatescript = "{virtualenv.scriptdir}/activate.ps1"
    replacements = [
        ("deactivate", "origdeactivate"),
    ]
    setpattern = """
New-Variable -Scope global -Name _OLD_SPIN_{name} -Value $env:{name}
$env:{name} = "{value}"
"""
    resetpattern = """
    if (Test-Path variable:_OLD_SPIN_{name}) {{
        $env:{name} = $variable:_OLD_SPIN_{name}
        Remove-Variable "_OLD_SPIN_{name}" -Scope global
    }}
"""
    script = """
{patchmarker}
{original}
function global:deactivate([switch] $NonDestructive) {{
    {resetters}
    if (!$NonDestructive) {{
        Remove-Item function:deactivate
        origdeactivate
    }}
}}

deactivate -nondestructive

{setters}
"""


class BatchActivate:
    patchmarker = "\nREM Patched by spin.builtin.virtualenv\n"
    activatescript = "{virtualenv.scriptdir}/activate.bat"
    replacements = ()
    setpattern = """
if not defined _OLD_SPIN_{name} goto ENDIFSPIN{name}1
    set "{name}=%_OLD_SPIN_{name}%"
:ENDIFSPIN{name}1
if defined _OLD_SPIN_{name} goto ENDIFSPIN{name}2
    set "_OLD_SPIN_{name}=%{name}%"
:ENDIFSPIN{name}2
set "{name}={value}"
"""
    resetpattern = ""
    script = """
@echo off
{patchmarker}
{original}
{setters}
"""


class BatchDeactivate:
    patchmarker = "\nREM Patched by spin.builtin.virtualenv\n"
    activatescript = "{virtualenv.scriptdir}/deactivate.bat"
    replacements = ()
    setpattern = ""
    resetpattern = """
if not defined _OLD_SPIN_{name} goto ENDIFVSPIN{name}
    set "{name}=%_OLD_SPIN_{name}%"
    set _OLD_SPIN_{name}=
:ENDIFVSPIN{name}
"""
    script = """
@echo off
{patchmarker}
{original}
{resetters}
"""


def finalize_provision(cfg):
    for schema in (
        BashActivate,
        BatchActivate,
        BatchDeactivate,
        PowershellActivate,
    ):
        patch_activate(schema)

    site_packages = (
        sh(
            "{virtualenv.python}",
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
            capture_output=True,
            silent=not cfg.verbose,
        )
        .stdout.decode()
        .strip()
    )
    info(f"Create {site_packages}/_set_env.pth")
    pthline = interpolate1(
        "import os; "
        "bindir='{virtualenv.bindir}'; "
        "os.environ['PATH'] = "
        "os.environ['PATH'] if bindir in os.environ['PATH'] "
        "else os.pathsep.join((bindir, os.environ['PATH']))\n"
    )
    writetext(f"{site_packages}/_set_env.pth", pthline)


@task("pipenv", add_help_option=False)
def pipenv(cfg, args):
    os.environ["PIPENV_VERBOSITY"] = "-1"
    if "INSIDE_EMACS" in os.environ:
        os.environ["PIPENV_COLORBLIND"] = "1"
        os.environ["PIPENV_HIDE_EMOJIS"] = "1"
        os.environ["PIPENV_NOSPIN"] = "1"
    pipenv = os.path.join(os.path.dirname(sys.executable), "pipenv")
    sh(pipenv, *args)


def install_to_venv(cfg, *args):
    args = interpolate(args)
    sh("pip", "install", cfg.quietflag, *args)


def provision(cfg):
    get_abi_tag(cfg)
    fresh_virtualenv = False
    if not exists("{virtualenv.venv}"):
        # Make sure the Python interpreter we'll use to create the
        # virtual environment has the virtualenv package installed.
        sh(
            "{python.interpreter}",
            "-mpip",
            cfg.quietflag,
            "install",
            "virtualenv",
            "packaging",
        )
        cmd = ["{python.interpreter}", "-mvirtualenv", cfg.quietflag]
        virtualenv = Command(*cmd)
        # do not download seeds, since we update pip later anyway
        virtualenv("-p", "{python.interpreter}", "{virtualenv.venv}")
        fresh_virtualenv = True

    # This sets PATH to the venv
    init(cfg)

    # Update pip in the venv
    if fresh_virtualenv:
        sh("python", "-mpip", cfg.quietflag, "install", "-U", "pip", "setuptools")

    # This is a much faster alternative to calling pip config; we
    # leave it active here for now, enjoying a faster spin until we
    # better understand the drawbacks.
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

    # If there is a setup.py, make an editable install (which
    # transitively also installs runtime dependencies of the
    # project).  FIXME: filename/location of setup.py should
    # probably be configurable
    if exists("setup.py"):
        install_to_venv(cfg, "-e", ".")

    with memoizer("{virtualenv.memo}") as m:

        replacements = cfg.get("devpackages", {})

        requirements = []

        def pipit(req):
            req = replacements.get(req, req)
            if not m.check(req):
                requirements.extend(req.split())
                m.add(req)

        # Plugins can define a 'venv_hook' function, to give them a
        # chance to do something with the virtual environment just
        # being provisioned (e.g. preparing the venv by adding pth
        # files or by adding packages with other installers like
        # easy_install).
        for plugin in cfg.topo_plugins:
            plugin_module = cfg.loaded[plugin]
            hook = getattr(plugin_module, "venv_hook", None)
            if hook is not None:
                logging.debug(f"{plugin_module.__name__}.venv_hook()")
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

        if requirements:
            install_to_venv(cfg, *requirements)


def cleanup(cfg):
    get_abi_tag(cfg)
    if exists("{virtualenv.venv}"):
        rmtree("{virtualenv.venv}")
