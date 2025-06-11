|Latest Version| |Python| |License|

`csspin` is maintained and published by `CONTACT Software GmbH`_.

`csspin` is the Python package that ships the task runner and CLI `spin` that
aims so solve the problems of *provisioning development environments* and
*standardizing workflows*. `spin` also automates the provisioning of tools and
other development requirements (including language stacks like Python,
Javascript/Node). As an example, for a project that uses Python and Javascript,
`spin` would:

* provision the requested version of Python
* provision the requested version of Node
* create a virtual development environment, in which the required versions of
  Python and Node can be used
* install tools and dependencies for development, testing, etc.

All with a single command: ``spin provision``!

Second, `spin` allows standardizing workflows, best practices and how
development tools are used, especially in a development group with many similar
projects that share practices and tools. It's plugin-based architecture allows
to define workflows executing multiple task in sequence using a single command.

By default, `spin` will automatically generate the right options and arguments
for the tools it runs, and show the user the precise commands. As a result,
*anyone* will be able to check out *any project*, run ``spin provision`` and
will be all set - Running a project's test suite becomes as simple as doing
``spin test`` etc.

A comprehensive documentation will be published soon.

Getting Started
---------------

`csspin` is available on PyPI and can be installed using pip, pipx or any other
Python package manager, e.g.:

.. code-block:: console

   python -m pip install csspin

Using spin
----------

As every other command line tool, `spin` can be run from the command line. The
command is simply called ``spin``. To see the available commands, run:

.. code-block:: console
   spin --help

Leveraging `spin`'s capabilities requires a project to be set up with a
`spinfile.yaml`. This file is a YAML file that defines the project, its tools,
and the workflows that `spin` can leverage. The `spinfile.yaml` is the
configuration file for `spin` and is typically located in the root directory of
the project.

A basic `spinfile.yaml` might look like this:

.. code-block:: yaml
    # spinfile.yaml
    spin:
      project_name: my_project

    # To develop plugins comfortably, install the packages editable as
    # follows and add the relevant plugins to the list 'plugins' below
    plugin_packages:
      - csspin_python

    # The list of plugins to be used for this project.
    plugins:
      - csspin_python.pytest

    python:
      version: 3.9.8
      requirements:
        - sphinx-click
        - sphinx-rtd-theme
        - pytest-mock

    pytest:
      opts: [-m, "not slow"]
      tests: [tests]


CPython Support Policies
------------------------

Our CPython support policy for spin aligns with the official CPython release
schedule, encompassing versions 3.9 through 3.13 (so far).

.. _`CONTACT Software GmbH`: https://contact-software.com
.. |Python| image:: https://img.shields.io/pypi/pyversions/csspin.svg?style=flat
    :target: https://pypi.python.org/pypi/csspin/
    :alt: Supported Python Versions
.. |Latest Version| image:: http://img.shields.io/pypi/v/csspin.svg?style=flat
    :target: https://pypi.python.org/pypi/csspin/
    :alt: Latest Package Version
.. |License| image:: http://img.shields.io/pypi/l/csspin.svg?style=flat
    :target: https://www.apache.org/licenses/LICENSE-2.0.txt
    :alt: License
