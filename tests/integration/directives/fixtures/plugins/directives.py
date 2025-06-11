# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

"""A dummy plugin used for testing directives"""

from csspin import config

defaults = config(
    test_append=config(opts=["1", "2", "3"]),
    # 'test_setting' is used to test append, prepend, interpolate without
    # explicit being set in spinfile.yaml.
    test_setting_1=["foo"],
    test_setting_2=["foo"],
)
