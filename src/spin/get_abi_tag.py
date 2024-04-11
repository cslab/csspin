# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/
#
# Ignoring the typing in this module since due to size of this file and
# environment-depending imports, one would have to ignore lots of rules in-line.
# type: ignore


"""
Helper script to find the ABI (application binary interface) tag of the target
interpreter.
"""


def get_abi_tag() -> None:
    """
    Function printing the ABI tag of the Python interpreter used.
    """
    try:
        try:
            from packaging import tags
        except ImportError:
            from pip._vendor.packaging import tags

        # tag for running interpreter (most important priority)
        tag = next(tags.sys_tags())
        print(tag.abi)
    except ImportError:
        from pip._internal.pep425tags import get_abi_tag

        print(get_abi_tag())


if __name__ == "__main__":
    get_abi_tag()
