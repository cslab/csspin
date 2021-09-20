# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# http://www.contact.de/

import os

from spin import config, option, sh, task

defaults = config(
    requires=[".python", ".preflight"],
    opts=[""],
    coverage_opts=["--cov=spin", "--cov=tests"],
    packages=["pytest", "pytest-cov", "pytest-tldr"],
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
        sh("{python.scriptdir}/pytest", *opts, *args)
