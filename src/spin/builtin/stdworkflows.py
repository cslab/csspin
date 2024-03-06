# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""
``Collection of standard SD workflows``
=======================================

.. click:: spin.builtin.preflight:test
   :prog: spin [test|tests]

.. click:: spin.builtin.preflight:cept
   :prog: spin [cept|acceptance]

.. click:: spin.builtin.preflight:preflight
   :prog: spin preflight
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


@task()
def preflight(ctx, instance: option("-i", "--instance")):
    """Pre-flight checks.

    Do this before committing else baby seals will die!
    """
    ctx.invoke(test, instance=instance)
    ctx.invoke(cept, instance=instance)
