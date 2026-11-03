# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2026 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""Local plugin providing a task group for testing shell completion"""

from csspin import group


@group(noenv=True)
def sbom() -> None:
    """Software bill of materials"""


@sbom.task(noenv=True)
def assemble() -> None:
    """Assemble"""


@sbom.task(noenv=True)
def build() -> None:
    """Build"""


@sbom.task(noenv=True)
def enrich() -> None:
    """Enrich"""


@sbom.task(noenv=True)
def quality() -> None:
    """Quality"""
