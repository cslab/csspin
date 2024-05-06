# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""
``Collection of standard SD workflows``
=======================================

.. click:: spin.builtin.stdworkflows:test
   :prog: spin [test|tests]

.. click:: spin.builtin.stdworkflows:cept
   :prog: spin [cept|acceptance]

.. click:: spin.builtin.stdworkflows:preflight
   :prog: spin preflight

.. click:: spin.builtin.stdworkflows:build
   :prog: spin build
"""

from spin import invoke, option, task


@task(aliases=["tests"])
def test(
    instance: option("-i", "--instance"),
    coverage: option("-c", "--coverage", is_flag=True),
    args,
):
    """Run all tests defined in this project."""
    invoke("test", instance=instance, coverage=coverage, args=args)


@task(aliases=["acceptance"])
def cept(
    cfg,
    instance: option("-i", "--instance"),
    coverage: option("-c", "--coverage", is_flag=True),
    args,
):
    """Run all acceptance tests defined in this project."""
    invoke("cept", instance=instance, coverage=coverage, args=args)


@task(aliases=["check"])
def lint(allsource: option("--all", "allsource", is_flag=True), args):
    """Run all linters defined in this project."""
    invoke("lint", allsource=allsource, args=args)


@task()
def preflight(ctx, instance: option("-i", "--instance")):
    """Pre-flight checks.

    Do this before committing else baby seals will die!
    """
    ctx.invoke(test, instance=instance)
    ctx.invoke(cept, instance=instance)


@task()
def build(cfg):
    """
    Workflow which triggers all build tasks.
    """
    invoke("build")
