# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, option, sh, task

defaults = config(
    requires=config(
        spin=[
            ".python",
            ".preflight",
        ],
        python=[
            "pytest",
            "pytest-cov",
            "pytest-tldr",
        ],
    ),
    opts=["-k", "not slow"],
    coverage_opts=[],
)


@task(when="test")
def pytest(
    cfg,
    instance: option("--instance", "instance"),
    coverage: option("--coverage", "coverage", is_flag=True),
    covreport: option("--cov-report", "covreport", default="html"),
    args,
):
    """Run the 'pytest' command."""
    if not args:
        if os.path.isdir("./tests"):
            args = ["./tests"]
    if args:
        opts = cfg.pytest.opts
        if coverage:
            opts.extend(cfg.pytest.coverage_opts)
            opts.append(f"--cov-report={covreport}")
        sh("pytest", *opts, *args)
