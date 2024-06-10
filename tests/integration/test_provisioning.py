# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2021 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/

import pytest

from spin import backtick, cli


@pytest.fixture(autouse=True)
def cfg():
    cli.load_config_tree(None)


def do_test(tmpdir, what, cmd, path="tests/integration/yamls", props=""):
    output = backtick(
        f"spin -p spin.cache={tmpdir} {props} -q -C {path} --env {tmpdir} -f"
        f" {what} --cleanup --provision {cmd}"
    )
    output = output.strip()
    return output


@pytest.mark.slow
def test_python(tmpdir):
    assert do_test(
        tmpdir, "python.yaml", "python --version", "tests/integration/testpkg"
    ).endswith("Python 3.9.6")


def test_python_use(tmpdir):
    output = do_test(
        tmpdir,
        "python.yaml",
        "python --version",
        "tests/integration/testpkg",
        "-p python.use=python",
    )
    assert "Python 3." in output


@pytest.mark.slow
def test_node(tmpdir):
    assert do_test(
        tmpdir,
        "node.yaml",
        "run node --version",
    ).endswith("v18.17.1")


@pytest.mark.slow
def test_java(tmpdir):
    output = do_test(
        tmpdir,
        "java.yaml",
        "run java --version",
    )
    assert "openjdk 19." in output


def test_build(tmpdir):
    assert "all build tasks" in do_test(
        tmpdir,
        "build.yaml",
        "build --help",
    )
