# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

"""
This plugin provisions a CONTACT Elements 15.x platform into a
spin-powered project. This cannot be done the standard way via
installing the corresponding Python package because CE 15.x doesnt
provide a such.

Instead, we provide the according Python modules via putting an
additional path configuration file which contains all necessary paths.
"""


import os

from spin import writetext, interpolate1, die, setenv


def provision(cfg):
    # The algo is as follows:
    # 1. Find the easy-install.pth file inside the CE installation tree
    # 2. Use the found file to compose a list of paths
    # 3. Write them into a path configuration file in venv's site-packages
    #    directory

    def ce_paths(interpreter_path):
        """
        Deduces:
        * The path to the shared libs folder and
        * The path to the site-packages folder
        inside the CE installation tree given the absolute path to
        CE's Python interpreter
        """
        segments = interpreter_path.split(os.sep)
        if os.name == "nt":
            topdir = os.path.join(segments[0], os.sep, *segments[1:-1])
            return (topdir, os.path.join(topdir, "Lib", "site-packages"))
        else:
            libdir = os.path.join(os.sep, *segments[:-2], "lib")
            return (
                os.path.join(libdir),
                os.path.join(libdir, "python2.7", "site-packages"),
            )

    def ce_pythonpath(sitepack_ce):
        """
        Composes a list if paths serving as roots when doing CE
        platform specific imports. Adding them to PYTHONPATH ensures
        that all relevant CE platform modules are importable.
        """
        paths = []
        seqments = sitepack_ce.split(os.sep)
        topdir = (
            os.path.join(seqments[0], os.sep, *seqments[1:-2])
            if os.name == "nt"
            else os.path.join(os.sep, *seqments[:-3])
        )
        paths.append(os.path.join(topdir, "cdb", "python"))

        for line in open(os.path.join(sitepack_ce, "easy-install.pth")):
            path = os.path.normpath(os.path.join(sitepack_ce, line.strip()))
            paths.append(path)

        return paths

    def venv_sppath(abitag):
        """
        Returns a relative path to venv's site-packages directory
        given the abitag of the according Python interpreter. Uses the
        convention established by PEP425
        (https://www.python.org/dev/peps/pep-0425/) to deduce the
        Python version related part of the path.
        """
        if os.name == "nt":
            return os.path.join("lib", "site-packages")
        else:
            import re

            tmp = re.match(".*([0-9]{2}).*", abitag).group(1)
            assert len(tmp) == 2
            postfix = "%s.%s" % tuple(tmp)
            return os.path.join("lib", "python%s" % postfix, "site-packages")

    ce_libpath, ce_sppath = ce_paths(interpolate1(cfg.python.use))
    if not os.path.exists(ce_libpath):
        die(
            "cannot provision CE platform since the library folder (%s) doesn't exist"
            % ce_libpath
        )

    if not os.path.exists(ce_sppath):
        die(
            "cannot provision CE platform since the site-packages folder (%s) doesn't exist"
            % ce_sppath
        )

    ce_pth_content = ce_pythonpath(ce_sppath)

    # Eggs in CE platform often depend from shared libs in the lib folder
    libpath_var = "PATH" if os.name == "nt" else "LD_LIBRARY_PATH"
    ce_pth_content.append(
        "import os; os.environ['%s'] = r'%s' + os.pathsep + os.environ.get('%s', '')"
        % (libpath_var, ce_libpath, libpath_var)
    )

    if os.name != "nt":
        setenv(
            f"export LD_LIBRARY_PATH=%s{os.pathsep}$LD_LIBRARY_PATH" % ce_libpath,
            LD_LIBRARY_PATH=os.pathsep.join((ce_libpath, os.environ.get("LD_LIBRARY_PATH", ""))),
        )

    venv_base_path = interpolate1(cfg.virtualenv.venv)
    ce_pth_path = os.path.join(
        venv_base_path, venv_sppath(cfg.virtualenv.abitag), "ce.pth"
    )
    writetext(ce_pth_path, "\n".join(ce_pth_content))

    # This prevents an ugly warning to be printed by CE's sitecustomize.py
    fake_cdb_package = os.path.join(venv_base_path, "cdb")
    if not os.path.isdir(fake_cdb_package):
        os.mkdir(fake_cdb_package)
