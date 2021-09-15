==========
About spin
==========

Spin is a task runner that aims so solve the problems of
**provisioning development environments** and **standardizing
workflows**.

Spin automates the provisioning of tools and other development
requirements (including language stacks like Python,
Javascript/Node). As an example, for a project that uses Python and
Javascript, `spin` would:

* provision the requested version of Python
* provision the requested version of Node
* create a virtual development environment, where the required
  versions of Python and Node can be used
* install tools for linting and testing etc.
* install pre-commit and install its hooks

All with a single command: ``spin --provision``!

Second, `spin` standardizes workflows, best practices and how
development tools are used, especially in a development group with
many similar projects that share practices and tools. For a typical
Python project the command ``spin preflight`` would:

* automatically run installed linters like :program:`flake8`
* run tests using :program:`pytest`

By default, `spin` will automatically generate the right options and
arguments for the tools it runs, and show the user the precise
commands.

Built-in workflows include ``build``, ``lint`` and ``tests`` (all
three will be run by ``preflight``), as well as ``bump-version``,
``package``, ``upload``, ``deploy`` etc. -- workflows are also
extensible by plugins.

As a result, *anyone* will be able to check out *any project*, run
``spin --provision`` and will be all set. Running a project's test
suite becomes as simple as doing ``spin test`` etc.


Spin's Plugin System
====================

The knowledge of how to do all this comes from two places: reusable
plugins and project-specific settings. `spin` has a plugin system,
where reusable bits are encapsulated in plugins like
`spin.builtin.python`, `spin.builtin.node`, `spin.builtin.pytest`
etc. Plugins automatically provision the tools they need, come with
meaningful default settings, provide new subcommands to `spin`
(e.g. ``spin pytest`` will launch :program:`pytest` in the development
environment), and hook into generic workflows. For example, the
`spin.builtin.pytest` plugin automatically hooks into the generic
``spin test`` command.  If your project one day decides to replace
`pytest` with something else, ``spin test`` will still do the right
thing.

`spin` has a library of built-in plugins for Python, Node, Java, C/C++
and common tools in those stacks. It's also easy to add plugins local
to a project, or create shared plugins that live as Python packages on
some Python package server or in a Git repository.


Project Settings and :file:`spinfile.yaml`
==========================================

The choice of plugins to use, and other project-specific settings, go
into a file called :file:`spinfile.yaml` in your project's root
directory. As an example, the most simple Python project would have a
:file:`spinfile.yaml` looking like so:

.. code-block:: yaml

   minimum-spin: 0.2
   plugins:
     - spin.builtin.python
   python:
     version: 3.9.6

``minimum-spin`` is required for all spinfiles, and indicates the
oldest version of spin, that can process that spinfile. ``plugins`` is
a list of Python modules, that are imported by spin and implement spin
plugins. In this case, ``spin.builtin.python`` is the built-in plugin,
that provides Python to a project. The ``python`` section is read by
the Python plugin, and ``version`` specifies the release of the Python
interpreter that this project wants to use.

Provisioning this project would install Python 3.9.6 and create a
virtual environment for working with the project:

.. code-block:: console

   $ spin --provision
   spin: cd /home/me/myproj
   spin: set PYENV_VERSION=3.9.6
   spin: python --version
   Python 3.9.6
   spin: python -mpip -q install -U virtualenv packaging
   spin: activate /home/me/.spin/env/myproj/cp38-manylinux_2_28_x86_64
   spin: pip -q install -e .

In this case, Python was provisioned by using `pyenv
<https://github.com/pyenv/pyenv>`_, which happened to be already
present in the user's home directory. This is not a requirement,
though. Depending on the platform -- and without a suitable Python
environment management tool -- `spin` would have downloaded a source
or binary distribution of Python, and install that into a cache
directory that is reused between different projects. In the same vein,
`spin` handles other stacks like Java and Node.

Now you want to test your project using `pytest`. All that is
necessary (besides writing the tests), is to add the
`spin.builtin.pytest` plugin to :file:`spinfile.yaml`:

.. code-block:: yaml
   :emphasize-lines: 4

   minimum-spin: 0.2
   plugins:
     - spin.builtin.python
     - spin.builtin.pytest
   python:
     version: 3.9.6

Provisioning again will automatically install the `pytest` package
from PyPI:

.. code-block:: console
   :emphasize-lines: 9

   $ spin --provision
   spin: cd /home/me/myproj
   spin: set PYENV_VERSION=3.9.6
   spin: python --version
   Python 3.9.6
   spin: python -mpip -q install -U virtualenv packaging
   spin: activate /home/me/.spin/env/myproj/cp38-manylinux_2_28_x86_64
   spin: pip -q install -e .
   spin: pip -q install pytest

Also, `spin` gained a new subcommand ``spin pytest``:

.. code-block:: console

   $ spin pytest
   spin: cd /home/me/myproj
   spin: set PYENV_VERSION=3.9.6
   spin: activate /home/me/.spin/env/myproj/cp38-manylinux_2_28_x86_64
   spin: /home/me/.spin/env/myproj/cp38-manylinux_2_28_x86_64/bin/pytest  ./tests
   ....E.......

After a while your project has been promoted to become a company-wide
standard, and thus it is required to follow your group's best
practices. Luckily, your team already has created a custom spin plugin
that comes with all the tools and settings required. You can simply
add that plugin to your :file:`spinfile.yaml`:

.. code-block:: yaml
   :emphasize-lines: 3-4,9

   minimum-spin: 0.2

   plugin-packages:
     - git+https://git.example.com/projstds#egg=projstds

   plugins:
     - spin.builtin.python
     - spin.builtin.pytest
     - mycompany.projstds
   python:
     version: 3.9.6

The ``plugin-packages`` key lists plugin packages that are installed
using :program:`pip` into a project specific plugin directory (which
notably is different from the project's virtual environment, in case
it is a Python project). The line reading "``- mycompany.projstds``"
makes spin import and use the plugin module ``mycompany.projstds``
that has been installed from the Git URL.

Your team's :program:`projstds` plugin comes with lots of tools and
predefined settings, among them :program:`pre-commit`: note how `spin`
automatically installs all the tools and sets up the
:program:`pre-commit` hooks.

.. code-block:: console
   :emphasize-lines: 9-11

   $ spin --provision
   spin: cd /home/me/myproj
   spin: set PYENV_VERSION=3.9.6
   spin: python --version
   Python 3.9.6
   spin: python -mpip -q install -U virtualenv packaging
   spin: activate /home/me/.spin/env/myproj/cp38-manylinux_2_28_x86_64
   spin: pip -q install -e .
   spin: pip -q install pytest pre-commit flake8 black flake8-isort ...
   spin: pre-commit install
   pre-commit installed at .git/hooks/pre-commit

This is a basic pattern working with spin: you modify your environment
by editing :file:`spinfile.yaml` and ask spin to re-provision the
environment.


Most Frequently Asked Questions
===============================

Why not ...?
------------

There are *many* tools that do things similar to `spin`, e.g. it is
customary to have standardized targets like ``clean``, ``all``,
``dist`` etc. for Unix Makefiles. Alas, we were not aware of tools
that at the same time:

* Are platform and technology stack independent: spin works with
  Python, Java, Node and C/C++ projects. Other stacks can be added by
  creating plugins.
* Can provision other software.
* Allow for re-usable definitions, that can be shared between many
  projects.
* Don't suck ;-)

Spin explicitly does *not* aim to be a build tool like GNU Make, CMake
or SCons, nor does it try to replace or improve other tools or tech
stacks: it is just a unpretentious way to store and re-use the
knowledge and conventions for installing and running development
tools.

Is it necessary to run everything via spin?
-------------------------------------------

Absolutely not! `spin` intentionally echoes the verbatim commands it
runs, to make users understand what is going on. It also provides
activation commands for development environments, to enable users to
"switch" to an environment provisioned by spin, and run the commands
manually. Spin plugins try to be well-behaved in this regard, and do
not silently modify the process environment, to make everything that
is going on transparent to the user.

Why YAML?
---------

Good question. I wasn't inclined to write a parser for this project,
and YAML seemed like the choice that sucked least: it has comments, it
is well supported by text editors, and its data model blends naturally
with the configuration tree paradigm of spin. YAML has the same
information model as JSON: supported data types include dictionaries,
lists and literals (mostly strings).

However, YAML is a complex beast. You can do all kinds of mischievous
tricks with YAML, and if you mess up the tree, the ``spin`` command
will most likely fail to run.
