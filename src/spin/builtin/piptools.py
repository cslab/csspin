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
    pip_compile=config(
        cmd="pip-compile",
        options=[
            "--generate-hashes",
            "--reuse-hashes",
            "--upgrade",
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
    def __init__(self, requirements_txt):
        self.requirements_txt = requirements_txt
        self.reqs = []

    def add(self, req):
        self.reqs.append(req)

    def lock(self, cfg):
        infile = self.requirements_txt + ".in"
        newtext = [f"{req}\n" for req in self.reqs]
        newtext.sort()
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
            sh(
                cfg.piptools.pip_compile.cmd,
                *cfg.piptools.pip_compile.options,
                infile,
                "-o",
                self.requirements_txt,
            )

    def get_txt(self):
        return [self.requirements_txt]


class PiptoolsProvisioner:
    def __init__(self):
        self.sets = {
            "": SetupPySet("setup.py", "requirements.txt"),
            "dev": DevSet("spin-reqs.txt"),
        }

    def add(self, setname, req):
        self.sets[setname].add(req)

    def lock(self, setname, cfg):
        self.sets[setname].lock(cfg)

    def sync(self, cfg):
        allreqs = []
        for reqset in self.sets.values():
            allreqs.extend(reqset.get_txt())
        sh(cfg.piptools.pip_sync.cmd, *cfg.piptools.pip_sync.options, *allreqs)

    def prerequisites(self, cfg):
        sh("pip", "install", cfg.quietflag, "pip-tools")


def configure(cfg):
    cfg.python.provisioner = PiptoolsProvisioner()
