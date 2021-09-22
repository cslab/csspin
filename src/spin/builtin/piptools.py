# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import difflib

from spin import (
    Path,
    config,
    echo,
    exists,
    is_up_to_date,
    readlines,
    readtext,
    sh,
    writelines,
)

defaults = config(
    requires=config(
        spin=[".python"],
        python=["setuptools"],
    ),
    hashes=False,
    pip_compile=config(
        cmd="pip-compile",
        options_hash=[
            "--generate-hashes",
            "--reuse-hashes",
        ],
        options=[
            # FIXME: we need a separate upgrade mechanism, otherwise
            # pip-tools will push us to latest (possible) for all deps
            # every time ###"--upgrade",
            "--allow-unsafe",
            "--header",
            "--annotate",
        ],
    ),
    pip_sync=config(
        cmd="pip-sync",
        options=[],
    ),
)


class SetupPySet:
    def __init__(self, setup_py, requirements_txt):
        self.setup_py = setup_py
        self.setup_cfg = setup_py.replace(".py", ".cfg")
        self.setup_dir = Path(setup_py).abspath().dirname().relpath()
        self.requirements_txt = requirements_txt

    def lock(self, cfg):
        if not is_up_to_date(self.requirements_txt, (self.setup_py, self.setup_cfg)):
            sh(
                cfg.piptools.pip_compile.cmd,
                *cfg.piptools.pip_compile.options,
                "-o",
                self.requirements_txt,
            )

    def add(self, req):
        raise NotImplementedError()

    def get_txt(self):
        return [self.requirements_txt]


class DevSet:
    def __init__(self, cfg, requirements_txt):
        self.cfg = cfg
        self.requirements_txt = requirements_txt
        self.reqs = set()

    def add(self, req):
        if req.startswith("-e") and self.cfg.piptools.hashes:
            die("Hashed dependencies are incompatible with editable installs.")
        self.reqs.add(req)

    def do_lock(self, cfg, reqset, options):
        requirements_txt = self.requirements_txt
        infile = requirements_txt + ".in"
        reqlist = list(reqset)
        reqlist.sort()
        newtext = [f"{req}\n" for req in reqlist]
        oldtext = []
        if exists(infile):
            oldtext = readlines(infile)
        if newtext != oldtext:
            echo(f"{infile} changed!")
            print(
                "".join(
                    difflib.context_diff(
                        oldtext, newtext, fromfile="before", tofile="after"
                    )
                )
            )
            writelines(infile, newtext)
            options = cfg.piptools.pip_compile.options
            if cfg.piptools.hashes:
                options.extend(cfg.piptools.pip_compile.options_hash)
            sh(
                cfg.piptools.pip_compile.cmd,
                *options,
                infile,
                "-o",
                requirements_txt,
            )

    def lock(self, cfg):
        self.do_lock(
            cfg,
            self.reqs,
            cfg.piptools.pip_compile.options,
        )

    def get_txt(self):
        out = [self.requirements_txt]
        return out


class PiptoolsProvisioner:
    def __init__(self, cfg):
        self.sets = {
            "": SetupPySet("setup.py", "requirements.txt"),
            "dev": DevSet(cfg, "spin-reqs.txt"),
        }

    def add(self, setname, req):
        self.sets[setname].add(req)

    def lock(self, setname, cfg):
        self.sets[setname].lock(cfg)

    def sync(self, cfg):
        allreqs = []
        for reqset in self.sets.values():
            allreqs.extend(reqset.get_txt())
        options = list(cfg.piptools.pip_sync.options)
        pipconf = cfg.python.pipconf.get("global", config())
        for option in ("index-url", "extra-index-url", "trusted-host"):
            value = pipconf.get(option, None)
            if value:
                options.extend([f"--{option}", value])
        sh(
            cfg.piptools.pip_sync.cmd,
            cfg.quietflag,
            *options,
            *allreqs,
        )
        if exists("setup.py"):
            sh("pip", "install", cfg.quietflag, "--no-deps", "-e", ".")

    def prerequisites(self, cfg):
        sh("pip", "install", cfg.quietflag, "pip-tools")


def configure(cfg):
    cfg.python.provisioner = PiptoolsProvisioner(cfg)
