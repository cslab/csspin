# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""

``preflight``
=============

.. click:: spin.builtin.preflight:test
   :prog: spin [test|tests]

.. click:: spin.builtin.preflight:lint
   :prog: spin [lint|check]

.. click:: spin.builtin.preflight:preflight
   :prog: spin preflight

"""

from spin import invoke, option, task


@task(aliases=["tests"])
def test(
    instance: option("--instance", "instance"),
    coverage: option("--coverage", "coverage", is_flag=True),
    args,
):
    """Run all tests defined in this project."""
    invoke("test", instance=instance, coverage=coverage, args=args)


@task(aliases=["check"])
def lint(allsource: option("--all", "allsource", is_flag=True), args):
    """Run all linters defined in this project."""
    invoke("lint", allsource=allsource, args=args)


@task()
def preflight(ctx, instance: option("--instance", "instance")):
    """Pre-flight checks.

    Do this before committing else baby seals will die!

    """
    ctx.invoke(test, instance=instance)
    ctx.invoke(lint, allsource=False)
