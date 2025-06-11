.. -*- coding: utf-8 -*-
   Copyright (C) 2024 CONTACT Software GmbH
   https://www.contact-software.com/

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

==========
About spin
==========

Spin is a task runner that aims so solve the problems of *provisioning
development environments* and *standardizing workflows*. Spin also automates the
provisioning of tools and other development requirements (including language
stacks like Python, Javascript/Node). As an example, for a project that uses
Python and Javascript, `spin` would:

* provision the requested version of Python
* provision the requested version of Node
* create a virtual development environment, in which the required versions of
  Python and Node can be used
* install tools and dependencies for development, testing, etc.

All with a single command: ``spin provision``!

Second, `spin` standardizes workflows, best practices and how development tools
are used, especially in a development group with many similar projects that
share practices and tools. It's plugin-based architecture allows to define
workflows executing multiple task in sequence using a single command.

By default, `spin` will automatically generate the right options and arguments
for the tools it runs, and show the user the precise commands. As a result,
*anyone* will be able to check out *any project*, run ``spin provision`` and
will be all set - Running a project's test suite becomes as simple as doing
``spin test`` etc.


Spin's plugin system
====================

The knowledge of how to do all this comes from two places: *reusable plugins*
and *project-specific settings*. `spin` has a plugin system, where reusable bits
are encapsulated in plugins like `csspin_python.python`_, `csspin_python.pytest`_,
`csspin_frontend.node`_ etc.

Plugins automatically provision the tools they need, come with meaningful
default settings, provide new subcommands to `spin` (e.g. ``spin pytest`` will
launch `pytest`_ in the development environment), and hook into generic
workflows. For example, the `csspin_python.pytest`_ plugin automatically hooks
into the generic ``spin test`` command in case `csspin_workflows.workflows`_ is
loaded. If your project one day decides to replace `pytest` with something else,
``spin test`` will still do the right thing.

`spin` has a small set of built-in plugins for example to run a shell command
in the project context. It's also easy to add local plugins to a project, or
create shared plugins that live as Python plugin-packages on some Python package
server or in a Git repository. A few of those addressing individual topics are
listed below.

.. list-table:: Selection of available plugin-packages
   :widths: 20 80
   :header-rows: 1

   * - Package name
     - Description
   * - `csspin_ce`_
     - required for CE16 development
   * - `csspin_workflows`_
     - collection of standard workflows
   * - `csspin_frontend`_
     - the frontend development kit
   * - `csspin_java`_
     - Java ist auch eine Insel
   * - `csspin_python`_
     - a must for Python development
   * - `csspin_vcs`_
     - enhancing version control system actions

.. _configuration-tree-system-label:

Spin's configuration tree system
================================

Spins configuration tree system manages project-specific and user-global
settings in a neat, hierarchical structure in form of a supercharged
``OrderedDict`` which enables *dot notation access* from within plugins, *parent
linking* as well as *location tracking* useful for debugging project
configurations.

Spin ships its own part of the configuration tree of which mosts it's properties
are directly assigned below ``spin``:

  .. code-block:: yaml
    :caption: Excerpt of spins builtin configuration tree
    :emphasize-lines: 1

    spin:
      data: Path('/home/developer/.local/share/spin')
      extra_index: None
      spinfile: Path('/home/developer/src/qs/spin/csspin/spinfile.yaml')
      ...

Plugins configured in project and user settings ship their own configuration
and thus extend the configuration tree.

  .. code-block:: yaml
    :caption: A plugin extending the configuration tree
    :emphasize-lines: 3

    spin:
      ...
    myplugin:
      setting1: ...
      setting2: ...


Spin is *building the configuration tree* during its execution by using the
following sources:

#. **Default configuration** that spin ships

#. **User specific configuration** in form of a ``global.yaml``
   (optional, see :ref:`writing-global-label`)

#. **Project configuration** provided by ``spinfile.yaml`` (see
   :ref:`writing-spinfile-label`)

#. **Environment variables** that updates or extends the configuration

#. **Command-line arguments and options** to update or extend the configuration

Provisioning a project using spin
=================================

The choice of plugins to use, and other project-specific settings go
into a file called :file:`spinfile.yaml` in your project's root
directory. Spin is just a task-runner, so lets take a most simple Python project
as an example to perform the provisioning.

.. code-block:: yaml
   :caption: Minimal :file:`spinfile.yaml` for a Python project "foo"

   spin:
     project_name: foo
   plugin_packages:
     - csspin_python
   plugins:
     - csspin_python.python
   python:
     version: 3.9.8

The ``spin.project_name`` property tells spin the name of the project we're
working on. Setting it may not be required, but is always recommended to avoid
errors where a project's directory name differs from the project name, for
example if a project ``foo`` has been cloned into the directory ``foo_new``.

The ``plugin_packages`` key lists plugin-packages that are installed using
:program:`pip` into a project-specific plugin directory (which notably is
different from the project's virtual environment, in case it is a Python
project).

``plugins`` is a list of Python modules of plugin-packages or local modules,
that are imported by spin and implement spin plugins. In this case,
`csspin_python.python`_ is a plugin from the ``csspin_python`` plugin-package, that
provides Python to a project. The ``python`` section is read by the Python
plugin, and ``version`` specifies the release of the Python interpreter that
this project wants to use.

Provisioning this project would download the `csspin_python`_ plugin-package and
its dependencies, install Python 3.9.8 and create a virtual environment from it
to then add the current project as editable install:

.. code-block:: console
   :caption: Provision a Python project using spin
   :emphasize-lines: 1,3,6,11,14

   $ spin provision
   spin: mkdir /home/developer/src/qs/spin/csspin/.spin/plugins
   spin: /home/developer/src/qs/spin/csspin/venv/bin/python3.12 -mpip install -q -t /home/developer/src/qs/spin/csspin/.spin/plugins csspin_python
   spin: set PYTHON_BUILD_CACHE_PATH=/home/developer/.local/share/spin/pyenv_cache
   spin: set PYTHON_CFLAGS=-DOPENSSL_NO_COMP
   spin: /home/developer/.local/share/spin/pyenv/plugins/python-build/bin/python-build 3.9.8 /home/developer/.local/share/spin/python/3.9.8
   Downloading Python-3.9.8.tar.xz...
   -> https://www.python.org/ftp/python/3.9.8/Python-3.9.8.tar.xz
   Installing Python-3.9.8...
   Installed Python-3.9.8 to /home/developer/.local/share/spin/python/3.9.8
   spin: /home/developer/src/qs/spin/csspin/venv/bin/python3.12 -mvirtualenv -q -p /home/developer/.local/share/spin/python/3.9.8/bin/python /home/developer/src/qs/spin/csspin/.spin/venv
   spin: activate /home/developer/src/qs/spin/csspin/.spin/venv
   spin: python -mpip -q install -U pip
   spin: pip install -q -e .

In this case, Python was provisioned using `pyenv
<https://github.com/pyenv/pyenv>`_ by downloading, caching and compiling the
distribution to create a Python virtual environment in which the current package
under development is installed. `spin` can handle other stacks like Java and
Node within the same venv, depending on their implementation.

Now you want to test your project using `pytest`_. All that is necessary
(besides writing the tests), is to add the `csspin_python.pytest`_ plugin to
:file:`spinfile.yaml`:

.. code-block:: yaml
   :caption: Minimal :file:`spinfile.yaml` to run the pytest plugin
   :emphasize-lines: 6

   spin:
     project_name: foo
   plugin_packages:
     - csspin_python
   plugins:
     - csspin_python.pytest
   python:
     version: 3.9.6

Spin will resolve the dependency from ``csspin_python.pytest`` to
``csspin_python.python`` without the need to define both plugins within
:file:`spinfile.yaml`.

Provisioning again will automatically install ``pytest`` and other packages
that ``csspin_python.pytest`` depends on from PyPI:

.. code-block:: console
   :caption: Provision the ``csspin_python.pytest`` plugin as well as its dependencies
   :emphasize-lines: 7

   $ spin provision
   spin: /home/developer/src/qs/spin/csspin/venv/bin/python3.12 -mpip install -q \
       -t /home/developer/src/qs/spin/csspin/.spin/plugins \
       csspin_python
   spin: activate /home/developer/src/qs/spin/csspin/.spin/venv
   spin: pip install -q pytest-cov pytest
   spin: pip install -q -e .

After provisioning, `spin` gained a new subcommand ``pytest``:

.. code-block:: console
   :caption: Execute the pytest subcommand
   :emphasize-lines: 1

   $ spin pytest
   spin -p pytest.tests=tests pytest
   spin: activate /home/developer/src/qs/spin/csspin/.spin/venv
   spin: pytest tests
   ======================= test session starts =================================
   platform linux -- Python 3.9.8, pytest-8.3.2, pluggy-1.5.0
   rootdir: /home/developer/src/qs/spin/csspin
   configfile: pyproject.toml
   plugins: cov-5.0.0
   collected 113 items
   tests/integration/test_provisioning.py ....
   ...

After a while your project has been promoted to become a company-wide standard,
and thus it is required to follow your group's best practices. Luckily, your
team already has created a custom spin plugin-package that comes with all the
tools and settings required. You can simply add that plugin to your
:file:`spinfile.yaml`:

.. code-block:: yaml
   :caption: :file:`spinfile.yaml` defining a plugin-package from a git-repository
   :emphasize-lines: 4,8,11-12
   :linenos:

   spin:
     project_name: foo
   plugin_packages:
     - git+https://git.example.com/projstds#egg=projstds
     - csspin_python
   plugins:
     - csspin_python.pytest
     - mycompany.projstds
   python:
     version: 3.9.6
   projstds:
     # Plugin settings goes here

The ``plugin_packages`` key lists plugin-packages that are installed using
:program:`pip` into a project specific plugin directory (which notably is
different from the project's virtual environment, in case it is a Python
project). Line 6 makes spin import and use the plugin module
``mycompany.projstds`` that has been installed from the Git URL defined in line
2.

Your team's :program:`projstds` plugin comes with lots of tools and predefined
settings, among them :program:`pre-commit`: note how `spin` automatically
installs all the tools and sets up the :program:`pre-commit` hooks.

.. code-block:: console
   :caption: Provisioning a plugin-package from a git-repository
   :emphasize-lines: 8-10

   $ spin provision
   spin: /home/developer/src/qs/spin/csspin/venv/bin/python3.12 -mpip install -q \
       -t /home/developer/src/qs/spin/csspin/.spin/plugins \
       csspin_python \
       git+https://git.example.com/projstds#egg=projstds
   spin: activate /home/developer/src/qs/spin/csspin/.spin/venv
   spin: pip -q install pytest pre-commit flake8 black flake8-isort ...
   spin: pre-commit install
   pre-commit installed at .git/hooks/pre-commit

This is a basic pattern when working with *spin*: you **modify your
environment** by editing :file:`spinfile.yaml` and let spin **re-provision the
environment**.


Most Frequently Asked Questions
===============================

Why not ...?
------------

There are *many* tools that do things similar to *spin*, e.g. it is customary to
have standardized targets like ``clean``, ``all``, ``dist`` etc. for Unix
Makefiles. Alas, we were not aware of tools that at the same time:

* Are platform and technology stack independent: spin works with Python, Java,
  Node and C/C++ projects. Other stacks can be added by creating plugins.
* Can provision other software.
* Allow for re-usable definitions, that can be shared between many projects.
* Don't suck ;-)

Spin explicitly does *not* aim to be a build tool like GNU Make, CMake or SCons,
nor does it try to replace or improve other tools or tech stacks: it is just a
unpretentious way to store and re-use the knowledge and conventions for
installing and running development tools.

Is it necessary to run everything via spin?
-------------------------------------------

Absolutely not! *spin* intentionally echoes the verbatim commands it runs, to
make users understand what is going on. It also provides activation commands for
development environments, to enable users to "switch" to an environment
provisioned by spin, and run arbitrary commands themselves. Spin plugins try to
be well-behaved in this regard, and do not silently modify the process
environment, to make everything that is going on transparent to the user.


Why YAML?
---------

Good question. The original author Frank Patz-Brockmann wasn't inclined to write
a parser for this project, and YAML seemed like the choice that sucked least: it
has comments, it is well supported by text editors, and its data model blends
naturally with the configuration tree paradigm of spin. YAML has the same
information model as JSON: supported data types include dictionaries, lists and
literals (mostly strings).

However, YAML is a complex beast. You can do all kinds of mischievous tricks
with YAML, and if you mess up the tree, the ``spin`` command will most likely
fail to run.

We also concluded that the standard python config files ``setup.cfg`` or
``pyproject.toml`` aren't quite fitting, as spin's :ref:`configuration tree
paradigm <configuration-tree-system-label>` is by far better visually
recognizable in the ``spinfile.yaml``.
