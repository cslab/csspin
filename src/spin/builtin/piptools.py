# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import difflib
import itertools

from spin import config, exists, info, is_up_to_date, readlines, sh, task, writelines

from .python import ProvisionerProtocol

defaults = config(
    requires=config(
        spin=[".python"],
        python=["setuptools", "pip-tools"],
    ),
    hashes=False,
    requirements="requirements-{platform.kind}.txt",
    requirements_sources=["setup.py", "setup.cfg"],
    extras="spin-reqs-{platform.kind}.txt",
    extras_in="{piptools.extras}.in",
    editable_options=[
        "--no-deps",
        "--use-feature=in-tree-build",
        "--no-build-isolation",
    ],
    pip_compile=config(
        cmd="pip-compile",
        options_hash=[
            "--generate-hashes",
            "--reuse-hashes",
        ],
        options=[
            "--allow-unsafe",
            "--header",
            "--annotate",
            "--no-emit-options",
        ],
        env=config(
            CUSTOM_COMPILE_COMMAND="spin --provision",
        ),
    ),
    pip_sync=config(
        cmd="pip-sync",
        options=[],
    ),
    prerequisites=["pip-tools"],
)


def pip_compile(cfg, *args):
    options = cfg.piptools.pip_compile.options
    if cfg.piptools.hashes:
        options.extend(cfg.piptools.pip_compile.options_hash)
    sh(
        cfg.piptools.pip_compile.cmd,
        *options,
        *args,
        env=cfg.piptools.pip_compile.env,
    )


class PiptoolsProvisioner(ProvisionerProtocol):
    def __init__(self, cfg):
        self.cfg = cfg
        self.extras = set()
        self.locks_updated = False

    def prerequisites(self, cfg):
        # use python -m pip otherwise this could lead to permission issues under
        # windows
        sh(
            cfg.python.python,
            "-m",
            "pip",
            "install",
            cfg.quietflag,
            *cfg.piptools.prerequisites,
        )

    def lock(self, cfg):
        if not is_up_to_date(
            cfg.piptools.requirements, cfg.piptools.requirements_sources
        ):
            pip_compile(cfg, "-o", cfg.piptools.requirements)
            self.locks_updated = True

    def add(self, req):
        if req.startswith("-e") and self.cfg.piptools.hashes:
            die("Hashed dependencies are incompatible with editable installs.")
        self.extras.add(req)

    def lock_extras(self, cfg):
        extras = list(self.extras)
        extras.sort()
        newtext = [f"{extra}\n" for extra in extras]
        oldtext = []
        if exists(cfg.piptools.extras_in):
            oldtext = readlines(cfg.piptools.extras_in)
        if newtext != oldtext or not exists(cfg.piptools.extras):
            # Show a nice diff of the updated .in file
            print(
                "".join(
                    difflib.context_diff(
                        oldtext, newtext, fromfile="before", tofile="after"
                    )
                )
            )
            writelines(cfg.piptools.extras_in, newtext)
            pip_compile(cfg, cfg.piptools.extras_in, "-o", cfg.piptools.extras)
            self.locks_updated = True

    def sync(self, cfg):
        if self.locks_updated and self.have_wheelhouse(cfg):
            info("Updating the wheelhouse!")
            self.wheelhouse(cfg)
        options = list(cfg.piptools.pip_sync.options)
        if self.have_wheelhouse(cfg):
            options.append("--no-index")
        sh(
            cfg.piptools.pip_sync.cmd,
            cfg.quietflag,
            *options,
            cfg.piptools.requirements,
            cfg.piptools.extras,
        )
        if exists("setup.py"):
            sh(
                "pip",
                "install",
                cfg.quietflag,
                *cfg.piptools.editable_options,
                "-e",
                ".",
            )

    def have_wheelhouse(self, cfg):
        return exists(cfg.python.wheelhouse)

    def wheelhouse(self, cfg):
        sh(
            "pip",
            "--exists-action",
            "b",
            "download",
            "-d",
            cfg.python.wheelhouse,
            "-r",
            cfg.piptools.requirements,
            "-r",
            cfg.piptools.extras,
        )


def configure(cfg):
    # We simply overwrite the default provisioner of the Python plugin
    # to replace the dependency management strategy.
    cfg.python.provisioner = PiptoolsProvisioner(cfg)


@task("python:wheelhouse")
def wheelhouse(cfg):
    """Download wheels to speed up provisioning new environments.

    Downloads the exact versions packages specified in the lock files
    into the wheelhouse for this project.
    """
    cfg.python.provisioner.wheelhouse(cfg)


@task("python:upgrade")
def python_upgrade(cfg, args):
    """Upgrade packages using pip-compile.

    With no arguments, upgrade all packages. If arguments are given,
    they are interpreted as the names of packages that are to be
    updated.

    Note that python:upgrade just modifies the lock files. To actually
    install upgrades, use 'spin --provision'. When a wheelhouse is
    used, the upgraded packages must be downloaded first using
    'python:wheelhouse'.
    """
    if not args:
        args = ["--upgrade"]
    else:
        args = itertools.chain.from_iterable(
            itertools.product(("--upgrade-package",), args)
        )
    pip_compile(cfg, "-o", cfg.piptools.requirements, *args)
    pip_compile(cfg, cfg.piptools.extras_in, "-o", cfg.piptools.extras, *args)
