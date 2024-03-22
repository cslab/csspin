# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""``python``
==========

This plugin provisions the requested version of the Python
programming languages.

On Linux and macOS, Python is installed by compiling from source
(implying, that Python's build requirements must be installed). On
Windows, pre-built binaries are downloaded using `nuget`.

If a user has `pyenv <https://github.com/pyenv/pyenv>`_ installed it
can be activated by setting ``python.user_pyenv`` in
:file:`global.yaml`.

To skip provisioning of Python and use an already installed version,
:py:data:`python.use` can be set to the name or the full path of an
interpreter:

.. code-block:: sh

   $ spin -p python.use=/usr/local/bin/python ...

Note: `spin` will install or update certain packages of that
interpreter, thus write access is required.

Tasks
-----

.. click:: spin.builtin.python:python
   :prog: spin python

.. click:: spin.builtin.python:wheel
   :prog: spin wheel


Properties
----------

* :py:data:`python.version` -- must be set to choose the
  required Python version
* :py:data:`python.interpreter` -- path to the Python interpreter

Note: don't use these properties when using `virtualenv`, they will
point to the base installation.

"""

import logging
import os
import re
import shutil
import sys

from click.exceptions import Abort

from spin import (
    EXPORTS,
    Command,
    Memoizer,
    Path,
    backtick,
    cd,
    config,
    die,
    download,
    echo,
    exists,
    get_requires,
    info,
    interpolate,
    interpolate1,
    mkdir,
    namespaces,
    parse_version,
    readtext,
    rmtree,
    setenv,
    sh,
    task,
    warn,
    writetext,
)

N = Path


WHEELHOUSE_MARKER = object()


defaults = config(
    pyenv=config(
        url="https://github.com/pyenv/pyenv.git",
        path=N("{spin.cache}/pyenv"),
        cache=N("{spin.cache}/cache"),
        python_build=(N("{python.pyenv.path}/plugins/python-build/bin/python-build")),
    ),
    user_pyenv=False,
    nuget=config(
        url="https://dist.nuget.org/win-x86-commandline/latest/nuget.exe",
        exe=N("{spin.cache}/nuget.exe"),
    ),
    version=None,
    plat_dir=N("{spin.cache}/{platform.tag}"),
    inst_dir=(
        N("{python.plat_dir}/python/{python.version}")
        if sys.platform != "win32"
        else N("{python.plat_dir}/python.{python.version}/tools")
    ),
    interpreter=N(
        "{python.inst_dir}/bin/python{platform.exe}"
        if sys.platform != "win32"
        else "{python.inst_dir}/python{platform.exe}"
    ),
    use=None,
    venv=N("{spin.env_base}/{python.abitag}-{platform.tag}"),
    memo=N("{python.venv}/spininfo.memo"),
    bindir=(N("{python.venv}/bin") if sys.platform != "win32" else "{python.venv}"),
    scriptdir=(
        N("{python.venv}/bin")
        if sys.platform != "win32"
        else N("{python.venv}/Scripts")
    ),
    python=N("{python.scriptdir}/python"),
    wheelhouse="{spin.env_base}/wheelhouse",
    pipconf=config(
        {
            "global": config(
                {"find-links": WHEELHOUSE_MARKER},
            ),
        },
    ),
    abitag=None,
    provisioner=None,
    extras=[],
)


def system_requirements(cfg):
    # This is our little database of system requirements for
    # provisioning Python; spin identifies platforms by a tuple
    # composed of the distro id and version e.g. ("debian", 10).
    return [
        # We intentionally leave out Tk, as it pulls in a lot of
        # graphics and X packages
        (
            lambda distro, version: distro in ("debian", "mint", "ubuntu"),
            {
                "apt-get": " ".join(
                    [
                        "build-essential",
                        "curl",
                        "git",
                        "libbz2-dev",
                        "libffi-dev",
                        "libkrb5-dev",
                        "liblzma-dev",
                        "libncursesw5-dev",
                        "libreadline-dev",
                        "libsqlite3-dev",
                        "libssl-dev",
                        "libxml2-dev",
                        "libxmlsec1-dev",
                        "make",
                        "xz-utils",
                        "zlib1g-dev",
                    ]
                ),
            },
        ),
        (
            lambda distro, version: (
                distro in ("centos", "fedora")
                and not (distro == "fedora" and version >= parse_version("22"))
            ),
            {
                "yum": (
                    "git gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite"
                    " sqlite-devel openssl-devel libffi-devel xz-devel"
                ),
            },
        ),
        (
            lambda distro, version: (
                distro == "fedora" and version >= parse_version("22")
            ),
            {
                "dnf": (
                    "git make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite"
                    " sqlite-devel openssl-devel libffi-devel xz-devel"
                ),
            },
        ),
        (
            lambda distro, version: distro == "darwin",
            {
                "brew": "git openssl readline sqlite3 xz zlib",
            },
        ),
        (
            # FIXME: no idea, whether this makes any sense
            lambda distro, version: re.match("opensuse", distro),
            {
                "zypper": (
                    "git gcc automake bzip2 libbz2-devel xz xz-devel openssl-devel"
                    " ncurses-devel readline-devel zlib-devel libffi-devel"
                    " sqlite3-devel"
                ),
            },
        ),
        (
            # FIXME: no idea, whether this makes any sense
            lambda distro, version: distro == "rhel",
            {
                "yum": (
                    "gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite"
                    " sqlite-devel openssl-devel libffi-devel xz-devel"
                )
            },
        ),
        (
            # On Windows, we use binaries from nuget (and the nuget
            # CLI is automatically installed into spin's cache, and
            # not a system dependency), so we'll have no particular
            # system dependencies.
            lambda distro, version: distro == "windows",
            {},
        ),
    ]


@task()
def python(args):
    """Run the Python interpreter used for this projects."""
    sh("python", *args)


@task("python:wheel", when="package")
def wheel(cfg):
    """Build a wheel of the current project."""
    try:
        echo("Building PEP 518 like wheel")
        sh("python", "-m", "build", "-w")
    except Abort:
        # TODO: Maybe think of another way to support
        # pyproject.toml _and_ setup.py style
        echo("Building does not seem to work, use legacy setup.py style")
        sh(
            "python",
            "setup.py",
            cfg.quietflag,
            "build",
            "-b",
            "{spin.env_base}/build",
            "bdist_wheel",
            "-d",
            "{spin.env_base}/dist",
        )


def pyenv_install(cfg):
    with namespaces(cfg.python):
        if cfg.python.user_pyenv:
            info("Using your existing pyenv installation ...")
            sh("pyenv install --skip-existing {version}")
            cfg.python.interpreter = backtick("pyenv which python --nosystem").strip()
        else:
            info("Installing Python {version} to {inst_dir}")
            # For Linux/macOS using the 'python-build' plugin from
            # pyenv is by far the most robust way to install a
            # version of Python.
            if not exists("{pyenv.path}"):
                sh("git clone {pyenv.url} {pyenv.path}")
            else:
                with cd("{pyenv.path}"):
                    sh("git pull")
            # we should set
            setenv(PYTHON_BUILD_CACHE_PATH=mkdir("{pyenv.cache}"))
            setenv(PYTHON_CFLAGS="-DOPENSSL_NO_COMP")
            sh("{pyenv.python_build} {version} {inst_dir}")


def nuget_install(cfg):
    if not exists("{python.nuget.exe}"):
        download("{python.nuget.url}", "{python.nuget.exe}")
    setenv(NUGET_HTTP_CACHE_PATH=N("{spin.cache}/nugetcache"))
    sh(
        "{python.nuget.exe}",
        "install",
        "-verbosity",
        "quiet",
        "-o",
        N("{spin.cache}/{platform.tag}"),
        "python",
        "-version",
        "{python.version}",
    )
    paths = interpolate1("{python.inst_dir};" + N("{python.inst_dir}/Scripts"))
    setenv(
        f"set PATH={paths}{os.pathsep}$PATH",
        PATH=os.pathsep.join((f"{paths}", os.environ["PATH"])),
    )
    sh("{python.interpreter} -m ensurepip --upgrade")
    sh(
        "{python.interpreter}",
        "-mpip",
        "install",
        cfg.quietflag,
        "-U",
        "pip",
        "wheel",
        "packaging",
    )


def provision(cfg):
    info("Checking {python.interpreter}")
    if not shutil.which(interpolate1(cfg.python.interpreter)):
        if sys.platform == "win32":
            nuget_install(cfg)
        else:
            # Everything else (Linux and macOS) uses pyenv
            pyenv_install(cfg)
    venv_provision(cfg)


def configure(cfg):
    if not cfg.python.version:
        die(
            "Spin's Python plugin no longer sets a default version.\n"
            "Please choose a version in spinfile.yaml by setting python.version"
        )
    if cfg.python.use:
        warn("python.version will be ignored, using '{python.use}' instead")
        cfg.python.interpreter = cfg.python.use
    elif cfg.python.user_pyenv:
        setenv(PYENV_VERSION="{python.version}")
        try:
            cfg.python.interpreter = backtick(
                "pyenv which python --nosystem",
                may_fail=True,
                silent=not cfg.verbose,
            ).strip()
        except Exception:
            pass


def init(cfg):
    if not cfg.python.use:
        logging.debug("Checking for %s", interpolate1("{python.interpreter}"))
        if not exists("{python.interpreter}"):
            die(
                "Python {python.version} has not been provisioned for this project. "
                "You might want to run spin with the'--provision' flag."
            )
    venv_init(cfg)


def get_abi_tag(cfg, cleanup=False):
    # To get the ABI tag, we've to call into the target interpreter,
    # which is not the one running the spin program. Not super cool,
    # firing up the interpreter just for that is slow.  ABI detection
    # has been moved to file which is then called by the interpreter.
    #
    # In cleanup mode, we don't abort but let the exception from
    # `sh()` propagate to be handled elsewhere.
    if not cfg.python.abitag:
        from spin import get_abi_tag

        abitag = backtick(
            "{python.interpreter}",
            get_abi_tag.__file__,
            may_fail=cleanup,
            silent=True,
        )
        cfg.python.abitag = abitag.strip()


# We won't activate more than once.
ACTIVATED = False


def venv_init(cfg):
    global ACTIVATED
    get_abi_tag(cfg)
    if os.environ.get("VIRTUAL_ENV", "") != cfg.python.venv and not ACTIVATED:
        activate_this = interpolate1("{python.scriptdir}/activate_this.py")
        if not exists(activate_this):
            die(
                "{python.venv} does not exist. You may want to provision it using"
                " spin --provision"
            )
        echo("activate {python.venv}")
        exec(open(activate_this).read(), {"__file__": activate_this})
        ACTIVATED = True


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
    activatescript = "{python.scriptdir}/activate"
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
    activatescript = "{python.scriptdir}/activate.ps1"
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
    activatescript = "{python.scriptdir}/activate.bat"
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
    activatescript = "{python.scriptdir}/deactivate.bat"
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
    cfg.python.provisioner.install(cfg)
    for schema in (
        BashActivate,
        BatchActivate,
        BatchDeactivate,
        PowershellActivate,
    ):
        patch_activate(schema)

    # TODO: this should be exported via the property tree
    site_packages = (
        sh(
            "python",
            "-c",
            'import sysconfig; print(sysconfig.get_path("purelib"))',
            capture_output=True,
            silent=not cfg.verbose,
        )
        .stdout.decode()
        .strip()
    )
    info(f"Create {site_packages}/_set_env.pth")
    pthline = interpolate1(
        "import os; "
        "bindir=r'{python.bindir}'; "
        "os.environ['PATH'] = "
        "os.environ['PATH'] if bindir in os.environ['PATH'] "
        "else os.pathsep.join((bindir, os.environ['PATH']))\n"
    )
    writetext(f"{site_packages}/_set_env.pth", pthline)


class ProvisionerProtocol:
    """An implementation of this protocol is used to provision
    dependencies to a virtual environment.

    Separate plugins, e.g. piptools, implement this interface and
    overwrite cfg.python.provisioner.

    """

    def prerequisites(self, cfg):
        """Provide requirements for the provisioning strategy."""

    def lock(self, cfg):
        """Lock the project's dependencies."""

    def add(self, req):
        """Add an extra dependency (development dependencies)."""

    def lock_extras(self, cfg):
        """Lock the extra dependencies."""

    def sync(self, cfg):
        """Synchronize the environment with the locked dependencies."""

    def install(self, cfg):
        """Install the project itself."""


class SimpleProvisioner(ProvisionerProtocol):
    """The simplest Python dependency provisioner using pip.

    This provisioner will never uninstall dependencies that are no
    longer required.
    """

    def __init__(self):
        # Note that self.requirements is effectively a set, since we
        # record requirements in the memoizer
        self.requirements = []
        self.m = Memoizer("{python.memo}")

    def prerequisites(self, cfg):
        # We'll need pip
        sh("python", "-mpip", cfg.quietflag, "install", "-U", "pip")

    def lock(self, cfg):
        """Noop"""

    def add(self, req):
        # Add the requirement if it's not already there.
        if not self.m.check(req):
            self.requirements.extend(req.split())
            self.m.add(req)

    def sync(self, cfg):
        # Install missing requirements.
        if self.requirements:
            sh("pip", "install", cfg.quietflag, *self.requirements)
        self.m.save()

    def install(self, cfg):
        # If there is a setup.py, make an editable install (which
        # transitively also installs runtime dependencies of the project).
        if any((exists("setup.py"), exists("setup.cfg"), exists("pyproject.toml"))):
            cmd = ["pip", "install", cfg.quietflag, "-e"]
            if cfg.python.extras:
                cmd.append(f".[{','.join(cfg.python.extras)}]")
            else:
                cmd.append(".")
            sh(*cmd)


def install_to_venv(cfg, *args):
    args = interpolate(args)


def venv_provision(cfg):
    get_abi_tag(cfg)
    fresh_virtualenv = False
    if not exists("{python.venv}"):
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
        virtualenv("-p", "{python.interpreter}", "{python.venv}")
        # Make sure pip is up to date
        sh(
            cfg.python.python,
            "-mpip",
            cfg.quietflag,
            "install",
            "-U",
            "pip",
        )
        fresh_virtualenv = True

    # This sets PATH to the venv
    init(cfg)

    if cfg.python.provisioner is None:
        cfg.python.provisioner = SimpleProvisioner()

    # Update pip.conf in the virtual environment
    text = []
    for section, settings in cfg.python.pipconf.items():
        text.append(f"[{section}]")
        for key, value in settings.items():
            if value == WHEELHOUSE_MARKER:
                if exists(cfg.python.wheelhouse):
                    value = cfg.python.wheelhouse
                else:
                    continue
            text.append(f"{key} = {interpolate1(value)}")
    if sys.platform == "win32":
        pipconf = "{python.venv}/pip.ini"
    else:
        pipconf = "{python.venv}/pip.conf"
    writetext(pipconf, "\n".join(text))

    # Update pip in the venv
    if fresh_virtualenv:
        cfg.python.provisioner.prerequisites(cfg)

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

    cfg.python.provisioner.lock(cfg)

    replacements = cfg.get("devpackages", {})

    def addreq(req):
        req = replacements.get(req, req)
        cfg.python.provisioner.add(interpolate1(req))

    # Install packages required by the project ('requirements')
    for req in cfg.python.get("requirements", []):
        addreq(req)

    # Install packages required by plugins used
    # ('<plugin>.requires.python')
    for plugin in cfg.topo_plugins:
        plugin_module = cfg.loaded[plugin]
        for req in get_requires(plugin_module.defaults, "python"):
            addreq(req)

    cfg.python.provisioner.lock_extras(cfg)
    cfg.python.provisioner.sync(cfg)


def cleanup(cfg):
    try:
        get_abi_tag(cfg, cleanup)
        if exists("{python.venv}"):
            rmtree("{python.venv}")
    except Exception:
        warn("cleanup: no Python interpreter installed")
        pass
