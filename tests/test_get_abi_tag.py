# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2024 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from spin.get_abi_tag import get_abi_tag

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


def test_get_abi_tag_packaging_tags_available(mocker: MockerFixture) -> None:
    """
    Test that checks the get_abi_tag function by mocking the packaging.tags
    import to (1.) ensure that the package is present and (2.) to validate that the
    printed value is the one that we expect.
    """
    tag_mock = MagicMock()
    tag_mock.abi = "cp310"
    tag_mock.sys_tags.return_value = iter((tag_mock,))
    mocker.patch.dict("sys.modules", {"packaging": MagicMock(tags=tag_mock)})

    with patch("builtins.print") as mock_print:
        get_abi_tag()
        mock_print.assert_called_once_with(tag_mock.abi)


def test_all_tags_unavailable(mocker: MockerFixture) -> None:
    """
    Test that checks the get_abi_tag function by mocking the
    pip._vendor.packaging and packaging imports to (1.) ensure that only the pip
    package is present and (2.) to validate that the printed value is the one that
    we expect. Due to setting packaging to None, we ensure that the expected
    import error was risen.
    """
    tag_mock = MagicMock()
    tag_mock.abi = "cp39"
    tag_mock.sys_tags.return_value = iter((tag_mock,))
    mocker.patch.dict(
        "sys.modules",
        {
            "packaging": None,
            "pip._vendor.packaging": MagicMock(tags=tag_mock),
        },
    )

    with patch("builtins.print") as mock_print:
        get_abi_tag()
        mock_print.assert_called_once_with(tag_mock.abi)


def test_packaging_tags_unavailable(mocker: MockerFixture) -> None:
    """
    Test that checks the get_abi_tag function by mocking the pip._vendor,
    pip._internal and packaging imports to (1.) ensure that the function
    "get_abi_tag" from pip._internal.pep425tags is present and (2.) to validate
    that the printed value is the one that we expect. Due to setting packaging
    and pip._vendor to None, we ensure that the expected import error were
    risen.
    """
    mock_abi_tag = MagicMock()
    mock_abi_tag.return_value = "cp33"
    mocker.patch.dict(
        "sys.modules",
        {
            "packaging": None,
            "pip._vendor": None,
            "pip._internal.pep425tags": MagicMock(get_abi_tag=mock_abi_tag),
        },
    )

    with patch("builtins.print") as mock_print:
        get_abi_tag()
        mock_print.assert_called_once_with(mock_abi_tag.return_value)
