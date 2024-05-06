# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""
Plugin flake8
=============

Adds `flake8 <https://flake8.pycqa.org/en/latest/>`_ to a
project. `flake8` plugins included by default are:

* flake8-isort
* flake8-comprehensions
* flake8-copyright
* flake8-polyfill
* flake8-fixme
* flake8-bugbear

.. click:: spin.builtin.flake8:flake8
   :prog: spin flake8

Properties
----------

* :py:data:`flake8.allsource` -- list of paths to check, when
  :option:`--all` is used. By default these are ``src`` and ``tests``
  in :py:data:`spin.project_root`.

.. todo:: flake8 argument handling
"""

import os

from spin import config, info, option, sh, task

defaults = config(
    exe="flake8",
    opts=["--exit-zero", f"-j{os.cpu_count()}"],
    requires=config(
        spin=[".python", ".vcs"],
        # These are the flake8 plugins we want to use. Maybe this should
        # be configurable in spinfile (candidates are "flake8-spellcheck"
        # or "flake8-cognitive-complexity", "dlint", "flake8-bandit" etc.)
        python=[
            "flake8",
            # "flake8-import-order",
            "flake8-isort",
            "flake8-comprehensions",
            "flake8-copyright",
            "flake8-polyfill",
            # These are not Py2-compatible; dont use them by default, as
            # they would break the flake8 task on Py2. Users which are
            # Py3-only may get them via overwriting the
            # "packages"-property in their spinfile
            #
            "flake8-fixme",
            "flake8-bugbear",
        ],
    ),
    allsource=["{spin.project_root}/src", "{spin.project_root}/tests"],
)


@task(when="lint")
def flake8(
    cfg,
    allsource: option(
        "--all",
        "allsource",
        help="Run flake8 on all Python files in the project",  # noqa
        is_flag=True,
    ),
    args,
):
    """Run flake8 to lint Python code."""
    if allsource:
        files = cfg.flake8.allsource
    else:
        files = args or cfg.vcs.modified
        files = [f for f in files if f.endswith(".py")]
    if files:
        info(f"flake8: Modified files: {files}")
        sh("{flake8.exe}", *cfg.flake8.opts, *files)
    else:
        info("flake8: No modified Python files.")
