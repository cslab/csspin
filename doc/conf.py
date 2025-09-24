# -*- mode: python; coding: utf-8 -*-
#
# Copyright (C) 2020 CONTACT Software GmbH
# All rights reserved.
# https://www.contact-software.com/
#
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

# -- Project information -----------------------------------------------------
import importlib.metadata

project = "csspin"
copyright = "2021, CONTACT Software GmbH"  # pylint: disable=redefined-builtin
author = "CONTACT Software GmbH"

# The full version, including alpha/beta/rc tags
release = importlib.metadata.version("csspin")


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx_click",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
]

todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    ".DS_Store",
    ".spin",
    ".venv",
    "links.rst",
    "Thumbs.db",
    "venv",
]

rst_epilog = ""
# Read link all targets from file
with open("links.rst", encoding="utf-8") as f:
    rst_epilog += f.read()


# -- Options for HTML output -------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", ("python.inv", None)),
    "click": (
        "https://click.palletsprojects.com/en/8.0.x/",
        (
            "click.inv",
            None,
        ),
    ),
    # could not find inventory file for the path package
    "path": ("https://path.readthedocs.io/en/latest/", (None,)),
}

# The theme to use for HTML and HTML Help pages. See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
html_favicon = "static/favicon.ico"
html_context = {
    "display_github": True,
    "github_user": "cslab",
    "github_repo": "csspin",
    "github_version": "master/doc/",
}
