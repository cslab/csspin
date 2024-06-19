# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

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
   :prog: spin python:wheel


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
from textwrap import dedent

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
    normpath,
    parse_version,
    readtext,
    rmtree,
    setenv,
    sh,
    task,
    warn,
    writetext,
)

WHEELHOUSE_MARKER = object()


defaults = config(
    inst_dir=(
        "{python.plat_dir}/python/{python.version}"
        if sys.platform != "win32"
        else "{python.plat_dir}/python.{python.version}/tools"
    ),
    interpreter=(
        "{python.inst_dir}/bin/python{platform.exe}"
        if sys.platform != "win32"
        else "{python.inst_dir}/python{platform.exe}"
    ),
    bindir="{python.venv}/bin" if sys.platform != "win32" else "{python.venv}",
    scriptdir=(
        "{python.venv}/bin" if sys.platform != "win32" else "{python.venv}/Scripts"
    ),
    pipconf=config({"global": config({"find-links": WHEELHOUSE_MARKER})}),
    provisioner=None,
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


@task()
def env():
    """Generate command to activate the virtual environment"""
    if sys.platform == "win32":
        # Don't care about cmd
        print(normpath("{python.scriptdir}", "activate.ps1"))
    else:
        print(f". {normpath('{python.scriptdir}', 'activate')}")


def pyenv_install(cfg):
    with namespaces(cfg.python):
        if cfg.python.user_pyenv:
            info("Using your existing pyenv installation ...")
            sh(f"pyenv install --skip-existing {cfg.python.version}")
            cfg.python.interpreter = backtick("pyenv which python --nosystem").strip()
        else:
            info("Installing Python {version} to {inst_dir}")
            # For Linux/macOS using the 'python-build' plugin from
            # pyenv is by far the most robust way to install a
            # version of Python.
            if not exists("{pyenv.path}"):
                sh(f"git clone {cfg.python.pyenv.url} {cfg.python.pyenv.path}")
            else:
                with cd(cfg.python.pyenv.path):
                    sh("git pull")
            # we should set
            setenv(PYTHON_BUILD_CACHE_PATH=mkdir(cfg.python.pyenv.cache))
            setenv(PYTHON_CFLAGS="-DOPENSSL_NO_COMP")
            sh(
                f"{cfg.python.pyenv.python_build} {cfg.python.version} {cfg.python.inst_dir}"
            )


def nuget_install(cfg):
    if not exists(cfg.python.nuget.exe):
        download(cfg.python.nuget.url, cfg.python.nuget.exe)
    setenv(NUGET_HTTP_CACHE_PATH=cfg.spin.cache / "nugetcache")
    sh(
        cfg.python.nuget.exe,
        "install",
        "-verbosity",
        "quiet",
        "-o",
        cfg.spin.cache / cfg.platform.tag,
        "python",
        "-version",
        cfg.python.version,
        "-source",
        cfg.python.nuget.source,
    )
    paths = os.pathsep.join([cfg.python.inst_dir, cfg.python.inst_dir / "Scripts"])
    setenv(
        f"set PATH={paths}{os.pathsep}$PATH",
        PATH=os.pathsep.join((paths, os.environ["PATH"])),
    )
    sh(f"{cfg.python.interpreter} -m ensurepip --upgrade")
    sh(
        cfg.python.interpreter,
        "-mpip",
        "install",
        cfg.quietflag,
        "-U",
        "pip",
        "wheel",
        "packaging",
    )


def provision(cfg):
    info(f"Checking {cfg.python.interpreter}")
    if not shutil.which(cfg.python.interpreter):
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
        except Exception:  # pylint: disable=broad-exception-caught
            # FIXME: add some proper logging
            pass


def init(cfg):
    if not cfg.python.use:
        logging.debug("Checking for %s", cfg.python.interpreter)
        if not exists(cfg.python.interpreter):
            die(
                f"Python {cfg.python.version} has not been provisioned for this"
                "project. You might want to run spin with the'--provision'"
                " flag."
            )
    venv_init(cfg)


# We won't activate more than once.
ACTIVATED = False


def venv_init(cfg):
    global ACTIVATED  # pylint: disable=global-statement
    if os.environ.get("VIRTUAL_ENV", "") != cfg.python.venv and not ACTIVATED:
        activate_this = cfg.python.scriptdir / "activate_this.py"
        if not exists(activate_this):
            die(
                f"{cfg.python.venv} does not exist. You may want to provision"
                " it using spin --provision"
            )
        echo(f"activate {cfg.python.venv}", resolve=True)
        with open(activate_this, encoding="utf-8") as file:
            exec(file.read(), {"__file__": activate_this})  # pylint: disable=exec-used
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
        # Removing the byte order marker (BOM) ensures the absence of those in
        # the final scripts. BOMs in executables are not fully supported in
        # Powershell.
        original = (
            readtext(f"{schema.activatescript}.bak").encode("utf-8").decode("utf-8-sig")
        )
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
    activatescript = Path("{python.scriptdir}") / "activate"
    replacements = [
        ("deactivate", "origdeactivate"),
    ]
    setpattern = dedent(
        """
        _OLD_SPIN_{name}="${name}"
        {name}="{value}"
        export {name}
        """
    )
    resetpattern = dedent(
        """
            if ! [ -z "${{_OLD_SPIN_{name}+_}}" ] ; then
                {name}="$_OLD_SPIN_{name}"
                export {name}
                unset _OLD_SPIN_{name}
            fi
        """
    )
    script = dedent(
        """
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
    )


class PowershellActivate:
    patchmarker = "\n## PATCHED BY spin.builtin.virtualenv\n"
    activatescript = Path("{python.scriptdir}") / "activate.ps1"
    replacements = [
        ("deactivate", "origdeactivate"),
    ]
    setpattern = dedent(
        """
        New-Variable -Scope global -Name _OLD_SPIN_{name} -Value $env:{name}
        $env:{name} = "{value}"
        """
    )
    resetpattern = dedent(
        """
            if (Test-Path variable:_OLD_SPIN_{name}) {{
                $env:{name} = $variable:_OLD_SPIN_{name}
                Remove-Variable "_OLD_SPIN_{name}" -Scope global
            }}
        """
    )
    script = dedent(
        """
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
    )


class BatchActivate:
    patchmarker = "\nREM Patched by spin.builtin.virtualenv\n"
    activatescript = Path("{python.scriptdir}") / "activate.bat"
    replacements = ()
    setpattern = dedent(
        """
        if not defined _OLD_SPIN_{name} goto ENDIFSPIN{name}1
            set "{name}=%_OLD_SPIN_{name}%"
        :ENDIFSPIN{name}1
        if defined _OLD_SPIN_{name} goto ENDIFSPIN{name}2
            set "_OLD_SPIN_{name}=%{name}%"
        :ENDIFSPIN{name}2
        set "{name}={value}"
        """
    )
    resetpattern = ""
    script = dedent(
        """
        @echo off
        {patchmarker}
        {original}
        {setters}
        """
    )


class BatchDeactivate:
    patchmarker = "\nREM Patched by spin.builtin.virtualenv\n"
    activatescript = Path("{python.scriptdir}") / "deactivate.bat"
    replacements = ()
    setpattern = ""
    resetpattern = dedent(
        """
        if not defined _OLD_SPIN_{name} goto ENDIFVSPIN{name}
            set "{name}=%_OLD_SPIN_{name}%"
            set _OLD_SPIN_{name}=
        :ENDIFVSPIN{name}
        """
    )
    script = dedent(
        """
        @echo off
        {patchmarker}
        {original}
        {resetters}
        """
    )


class PythonActivate:
    patchmarker = "# Patched by spin.builtin.virtualenv\n"
    activatescript = "{python.scriptdir}/activate_this.py"
    replacements = ()
    setpattern = 'os.environ["{name}"] = r"{value}"'
    resetpattern = ""
    script = dedent(
        """
        {patchmarker}
        {original}
        {setters}
        """
    )


def finalize_provision(cfg):
    cfg.python.provisioner.install(cfg)
    for schema in (
        BashActivate,
        BatchActivate,
        BatchDeactivate,
        PowershellActivate,
        PythonActivate,
    ):
        patch_activate(schema)

    # TODO: this should be exported via the property tree
    site_packages = Path(
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
    info(f"Create {(setenv_path := str(site_packages / '_set_env.pth'))}")
    pthline = interpolate1(
        "import os; "
        "bindir=r'{python.bindir}'; "
        "os.environ['PATH'] = "
        "os.environ['PATH'] if bindir in os.environ['PATH'] "
        "else os.pathsep.join((bindir, os.environ['PATH']))\n"
    )
    writetext(setenv_path, pthline)


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

    def add(self, req, devpackage=False):
        """Add an extra dependency (incl. development ones)."""

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
        self.requirements = set()
        self.devpackages = set()
        self.m = Memoizer("{python.memo}")

    def prerequisites(self, cfg):
        # We'll need pip
        sh("python", "-mpip", cfg.quietflag, "install", "-U", "pip")

    def lock(self, cfg):
        """Noop"""

    def add(self, req, devpackage=False):
        # Add the requirement or devpackage if not already there.
        if not self.m.check(req):
            lst = self.devpackages if devpackage else self.requirements
            lst.add(req)
            self.m.add(req)

    def sync(self, cfg):
        # Install missing requirements.
        if self.requirements:
            sh("pip", "install", cfg.quietflag, *self._split(self.requirements))
            self.m.save()

    def install(self, cfg):
        if self.devpackages:
            sh("pip", "install", cfg.quietflag, *self._split(self.devpackages))
            self.m.save()

        # If there is a setup.py, make an editable install (which
        # transitively also installs runtime dependencies of the project).
        if any((exists("setup.py"), exists("setup.cfg"), exists("pyproject.toml"))):
            cmd = ["pip", "install", cfg.quietflag, "-e"]
            if cfg.python.extras:
                cmd.append(f".[{','.join(cfg.python.extras)}]")
            else:
                cmd.append(".")
            sh(*cmd)

        # Verify dependency compatibility of installed packages
        pip_check = sh("pip", "check", may_fail=True, capture_output=True)
        if pip_check.returncode:
            die(pip_check.stdout)

    def _split(self, reqset):
        """to pass whitespace-less args to sh()"""
        reqlist = []
        for req in reqset:
            reqlist.extend(req.split())
        return reqlist


def install_to_venv(cfg, *args):
    args = interpolate(args)


def venv_provision(cfg):
    fresh_virtualenv = False
    if not exists(cfg.python.venv):
        # virtualenv is guaranteed to be available like this
        # as we declared it as one of spin's dependencies
        cmd = [sys.executable, "-mvirtualenv", cfg.quietflag]
        virtualenv = Command(*cmd)
        # do not download seeds, since we update pip later anyway
        virtualenv("-p", cfg.python.interpreter, cfg.python.venv)
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
        pipconf = cfg.python.venv / "pip.ini"
    else:
        pipconf = cfg.python.venv / "pip.conf"
    writetext(pipconf, "\n".join(text))

    # Establish the prerequisites
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

    # Install packages required by the project ('requirements')
    for req in cfg.python.get("requirements", []):
        cfg.python.provisioner.add(interpolate1(req))

    # Install development packages required by the project ('devpackages')
    for pkgspec in cfg.python.get("devpackages", []):
        cfg.python.provisioner.add(interpolate1(pkgspec), True)

    # Install packages required by plugins used
    # ('<plugin>.requires.python')
    for plugin in cfg.topo_plugins:
        plugin_module = cfg.loaded[plugin]
        for req in get_requires(plugin_module.defaults, "python"):
            cfg.python.provisioner.add(interpolate1(req))

    cfg.python.provisioner.lock_extras(cfg)
    cfg.python.provisioner.sync(cfg)


def cleanup(cfg):
    try:
        if exists(cfg.python.venv):
            rmtree(cfg.python.venv)
    except Exception:  # pylint: disable=broad-exception-caught
        warn("cleanup: no Python interpreter installed")
        pass
