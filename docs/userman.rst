.. -*- coding: utf-8 -*-
   Copyright (C) 2024 CONTACT Software GmbH
   All rights reserved.
   https://www.contact-software.com/

==========
Using spin
==========

Spin, or better the spin plugins, do just two things: they **provision
development environments**, and **run development tools**.

.. index::
   single: environment

An **environment** is a directory, where spin creates language stack specific
things, e.g. for Python it creates a Python virtual environment. Then, the
project's runtime and development dependencies and the project itself is
installed into the environment. Environments must be created explicitly, by
passing the command line option :option:`--provision <spin --provision>` to
spin. Spin will refuse to run most tasks before an environment has been created.

Environments are generally created below ``.spin`` which is located in the
project root directory. Spin and its plugins try hard to place everything that
is generated while provisioning, building, testing etc. in the environment
directory or the users cache directory to keep the source tree clean.

**Plugins** are Python modules that leverage spin's API to do one ore more of
the following:

* register new subcommands; e.g. the `spin_python.python`_ plugin registers a
  subcommand ``python``; this can be verified by calling ``spin
  --help``, which displays all know subcommands.

* declare plugin dependencies, e.g. the `spin_python.pytest`_ plugin depends on
  `spin_python.python`_ because we need Python to actually run ``pytest``.

* declare package requirements, that are installed into a virtual environment.
  For example, the `spin_python.pytest`_ plugin requires `pytest`_ and
  `pytest-cov <https://pytest-cov.readthedocs.io/en/latest/>`_ and some of its
  extensions to be installed.

* declare *hooks* that are called while spin runs; e.g. the
  `spin_python.python`_ plugin declares a hook that provisions the required
  Python release.

**Tasks** are commands run by spin plugins inside an environment, e.g. the
`spin_python.python`_ plugin registers a ``python`` task, that simply runs the
Python interpreter.


.. _writing-spinfile-label:

Writing ``spinfile.yaml``
=========================

Spin expects a `YAML <https://yaml.org/>`_ file named ``spinfile.yaml`` in the
top-level directory of the project that lists the plugins to use, parameters for
task etc. This file is used to construct a :ref:`configuration tree
<configuration-tree-system-label>`, a nested data structure that defines the
project and the behavior of spin and the plugins. The configuration tree is
built from (in this order):

* The default configuration of spin itself and each plugin. E.g. plugin default
  values defined within each plugin module.
* The settings from ``spinfile.yaml`` complement (or override) the defaults.
* If it exists, user-specific settings are read from
  ``$XDG_CONFIG_HOME/spin/global.yaml`` and complement the project configuration
  tree; a use-case for this can be to globally set a proxy for accessing
  specific resources. This behavior can be disabled by setting the environment
  variable ``SPIN_DISABLE_GLOBAL_YAML`` to ``True``.
* Environment variables as defined
  :ref:`here <environment-as-input-channel-label>`
* Command line settings given by :option:`-p prop=value <spin -p>`,
  :option:`--ap prop=value <spin --ap>` and :option:`--pp prop=value <spin
  --pp>` can override or extend all non-internal settings; a typical use case is
  to override the version of the Python interpreter using ``spin -p
  python.use=/usr/bin/python`` in a CI build to avoid provisioning a Python
  interpreter on each run.


To do anything useful, at least one plugin must be included. Here, we use the
`spin_python.python`_ plugin, that also requires a version.

.. code-block:: yaml
   :caption: Minimal :file:`spinfile.yaml` for a Python project

   plugins:
     - spin_python.python
   python:
     version: 3.11.9

You can visualize the configuration tree for this minimal example by using the
:option:`--dump <spin --dump>` option (many lines left out):

.. code-block:: console
   :emphasize-lines: 5-6,8

   $ spin --dump
   src/spin/schema.yaml:17: |spin:
   src/spin/cli.py:612:     |  spinfile: Path('/home/bts/src/qs/spin/cs.spin/spinfile.yaml')
   ... more lines ...
   spinfile.yaml:14:        |plugins:
                            |  - 'spin.builtin.python'
   src/spin/cli.py:137:     |python:
   spinfile.yaml:21:        |  version: '3.9.8'
   ... even more lines ...

:option:`--dump <spin --dump>` shows the complete configuration tree, and for
each setting, where it came from. The highlighted lines are from the project
spinfile, while the rest are spin's default settings or dynamically generated.

There are dozens of settings defined by the spin framework, and each plugin
comes with its own set of settings and uses settings from other plugins and
spins API.


Plugin-packages
---------------

Plugins are Python modules, and they are imported by spin using their (full)
import name. Plugin import names are listed under the :py:data:`plugins` key. It
is important to note, that plugin modules and spin itself are totally separate
from your project, even if it also uses Python. A common way to distribute and
access plugins is via :py:data:`plugin-packages`, which are Python packages
containing multiple plugins.

The example below demonstrates how to declare a plugin package and selected
plugins to be installed from the default Python package index.

.. code-block:: yaml
   :caption: Example: :file:`spinfile.yaml` configuration for importing plugins

   plugin-packages:
     - spin_python
   plugins:
     - spin_python.behave
     - spin_python.pytest

To not repeat yourself, this can be expressed more compact by nesting the
plugins under some namespaces. The next example is equivalent to the previous
one:

.. code-block:: yaml
   :caption: Example: :file:`spinfile.yaml` configuration for importing plugins (short)

   plugin-packages:
     - spin_python
   plugins:
     - spin_python:
       - behave
       - pytest

Plugin packages versions can also be constrained and even installations from
git-repositories is possible:

.. code-block:: yaml
    :caption: Example: Additional ways to install plugin-packages

    plugin-packages:
     - someones-spin-plugins~=2.0
     - git+https://git.example.com/projstds#egg=projstds

Spin will install plugin packages into :file:`.spin/plugins`.

Local plugins
-------------

Spin supports project-specific plugins local to a project. You can specify a
list of paths relative to the project root directory, where spin looks for local
plugins using the ``plugin-path`` key:

.. code-block:: yaml
   :caption: Importing plugins from a local path

   plugin-path:
     - plugins/deployment
     - plugins/building

   # Assuming deploy.py is in one of those directories, it can now be loaded
   plugins:
     - deploy
     - ...

Interpolation
-------------

Settings in the :ref:`configuration tree <configuration-tree-system-label>` can
refer to other settings by using *string interpolation*: path expressions
surrounded by braces are replaced by the setting given. E.g. ``{spin.cache}`` is
the setting ``cache`` in the subtree ``spin`` and its semantic is to hold the
path where spin and it's plugins are caching files. Strings are interpolated
against the configuration tree and environment variables until they no longer
contain an expression. Expressions are resolved recursively so an interpolation
can result in another interpolatable expression, that will be interpolated as
well, until the process reaches its fix point.

In YAML, braces are syntactical meta-characters that indicate a literal
dictionary (like in JSON, of which YAML is super-set). Settings using string
interpolation must therefore be quoted while escaping can be done via double
curly braces (see :py:func:`spin.interpolate1`).

The following example demonstrates how to construct ``upload.url`` by using
``upload.user`` provided by the configuration tree and ``UPLOAD_PASSWORD`` from
the environment.

.. code-block:: yaml
   :caption: Demonstrating interpolation on a fictional upload plugin within :file:`spinfile.yaml`

   ...
   upload:
      user: buildbot
      url: "{upload.user}@{UPLOAD_PASSWORD}/upload"

For more information about the interpolation

Extra-tasks
-----------

If a project needs a few extra tasks, those can be defined explicitly in
spinfile using ``extra-tasks``: for each new task a key is added, and each task
can define the following sub-keys:

* ``script``: a list of shell commands
* ``env``: a dictionary of environment variables, that should be set
  when running the shell commands
* ``spin``: a list of spin commands (without ``spin``)
* ``help``: help text to display

The following example adds ``pipx-install`` and ``all`` as tasks to
spin:

.. code-block:: yaml

   ...
   extra-tasks:
     pipx-install:
       env:
         USE_EMOJI: no
       script:
         - pipx install --force --editable .
       help: This installs spin via pipx
     all:
       spin:
         - build
         - tests
         - docs
         - package
         - upload
       help: Run a set of available tasks


Build-rules
-----------

Spin has a *very* simple built-in facility for automatically generating target
files depending on source files -- similar to Unix Make, although *much* more
primitive.

.. Attention:: Don't use this to simulate a real build tool!

Dependencies are declared under the ``build-rules`` key as follows:

* each sub-key is a target; tasks are "pseudo" targets prefixed with
  ``"task "`` (exactly one space!)

* each target can have the following keys:

  * ``sources``: a path or a list of paths that are inputs for the
    target

  * ``script``: a list of shell commands that are executed to re-build
    the target if necessary

  * ``spin``: a list of spin tasks that are executed to re-build the
    target if necessary

.. todo This should support ``env`` as well!
.. FIXME: provide another non-spin related example

Here is an example from a previous version of the spin project
itself.

**Example 1**: The reference documentation for the spinfile schema is generated from
a schema file by a spin task. The resulting :file:`docs/schemaref.rst`
is updated whenever :program:`spin docs` is executed, and
:file:`src/spin/schema.yaml` is more recent than
:file:`schemaref.rst`:

.. code-block:: yaml
   :caption: Custom `build-rules` to automate documentation building

   build-rules:
     task docs:
       sources: docs/schemaref.rst
     docs/schemaref.rst:
       sources: [src/spin/schema.yaml]
       spin:
         - schemadoc -o docs/schemaref.rst


Directives
----------

Similar to :option:`--pp <spin --prepend-properties>` and
:option:`--ap <spin --append-properties>`, lists can also be extended by
definitions within the `spinfile.yaml`

.. code-block:: yaml
   :caption: Extending lists via ``spinfile.yaml``

   myplugin:
     # assuming default values for 'opts' provided by the plugin is:
     # opts: [--option=value]
     append opts: [music]
     prepend opts: --quiet

   ---
   # The myplugins subtree will by transformed by spin into:
   myplugin:
     opts: [--quiet, --option=value, music]


.. _writing-global-label:

Writing ``global.yaml``
=======================

``spin`` looks for a file called ``global.yaml`` in ``$XDG_CONFIG_HOME/spin``.
Settings from this file are merged into the project :ref:`configuration tree
<configuration-tree-system-label>`. This
facility can be used to provide user/machine specific settings like in the
example below.

.. code-block:: yaml

   # Settings for frank@haskell

   # I use a local devpi mirror. Set its properties here.
   devpi:
     user: frank
     url: http://haskell:4033
     stage: "{devpi.url}/{devpi.user}/staging"

   # Override pipconf settings in virtualenv to use my devpi mirror.
   python:
     pipconf:
       global:
         extra-index-url: "{devpi.stage}/+simple/"

     # Packages whose sources are expected to be available locally
     # and potentially require additional tools (e.g. Node) to be
     # built and installed.
     devpackages:
       - -e {HOME}/Projects/cpytoolchain


.. _environment-as-input-channel-label:

Environment variables
=====================

cs.spin provides a command-line interface as documented in spins
:ref:`cliref-label`. Besides that, modifying the configuration tree via the
environment is a crucial feature which possible via:

- ``SPIN_`` **-prefix**:
   - Used to modify the options directly passed to cs.spin itself.
   - Is subject of the natural limitation of assigning values to a property,
     which could be assigned by multiple values at once, i.e. ``SPIN_P`` can
     obviously only used once: ``SPIN_P="pytest.opts=-vv"``.
- ``SPIN_TREE_`` **-prefix**
   - Dedicated to defining and modifying configuration tree entries via
     environment variables (i.e. affecting how tasks calling tools). This method
     mirrors the effect of passing configuration parameters using the ``-p``
     option directly via CLI.
   - Accessing nested elements, e.g. ``pytest.opts`` is possible via double
     underscores: ``SPIN_TREE_PYTEST__OPTS="[-m, not slow]"``.
   - Limitations are given by the circumstance that due to accessing nested
     properties via double underscore, configuration tree keys, with leading or
     trailing underscores as well as those that include multiple underscores in
     order can't be accessed like this. Same counts for keys that can't be
     represented as environment variable.


Builtin tasks
=============

``system-provision``
--------------------

The ``system-provision`` task prints the system requirements of
the project as well as individual plugins that must be installed by the user
manually in order to provision the project.

Projects can define their system requirements within ``spinfile.yaml``:

.. code-block:: yaml
  :caption: Defining project specific system requirements in ``spinfile.yaml``

  system-requirements:
    distro in ("debian", "ubuntu"):
      apt-get: git curl
    distro=="fedora" and version>=parse_version("22"):
      dnf: git curl

Depending on the os, a call of ``spin system-provision`` prints a command that
can be used to install required dependencies. The output depends on the host OS.
For reviewing required dependencies on other distributions the following syntax
can be used: ``spin system-provision [<distro> [<version>]]``.

Troubleshooting
===============

At every place where people work, there will be some errors, so feel free to
read the following characteristics of spin and it's behavior to avoid some
sources of error in advance.

Order of property overriding
----------------------------

Environment variables can be used to set and modify properties of the
configuration tree, nevertheless, the CLI always wins, i.e. values passed via
the environment will be overridden, in case the same keys were modified via CLI.

.. code-block:: bash
  :caption: Overriding settings of the configuration tree

  # SPIN_P will be overridden by values passed via "-p"
  SPIN_P="pytest.opts=[-vv]" spin -p pytest.opts="[-m, wip]" pytest

  # SPIN_TREE_PYTEST__OPS will be overridden by values passed via
  #   "-p pytest.opts"
  SPIN_TREE_PYTEST__OPS="[-m, 'not slow']" spin \
    -p pytest.opts="[-m, wip]" pytest

  # SPIN_P will be overridden by SPIN_TREE_PYTEST__OPTS
  #   AND: SPIN_TREE_PYTEST__OPTS will be overridden by values passed via
  #   "-p pytest.opts"
  SPIN_P="pytest.opts=[-vv]" SPIN_TREE_PYTEST__OPTS="[-m, 'not slow']" spin \
    -p pytest.opts="[-m, wip]" pytest

One source of error to avoid is: assigning values to be interpolated to
environment variables, that will be overridden:

.. code-block:: bash
  :caption: Negative Examples: How environment variables should not be used.

  # The python.version passed via CLI is not used in coverage.opts, since
  # pytest.coverage_opts is set to the default python.version=3.9.8, before
  # python.version was overridden via CLI.
  SPIN_TREE_pytest__coverage_opts="[{python.version}]" spin \
    -p python.version="3.11.7" \
    -p pytest.opts="[{python.version}]" --dump | grep -A4 "|pytest:"
  src/spin/cli.py:142:            |pytest:
  command-line:0:                 |  opts:
                                  |    - '3.11.7'
  command-line:0:                 |  coverage_opts:
                                  |    - '3.9.8'

  # The order of -p calls makes a difference too.
  SPIN_TREE_pytest__coverage_opts="[{python.version}]" spin \
    -p pytest.opts="[{python.version}]" \
    -p python.version="3.11.7" --dump | grep -A4 "|pytest:"
  src/spin/cli.py:142:            |pytest:
  command-line:0:                 |  opts:
                                  |    - '3.9.8'
  command-line:0:                 |  coverage_opts:
                                  |    - '3.9.8'

  # The correct way in both cases would be to first override python.version via
  # the environment:
  SPIN_TREE_PYTHON__VERSION="3.11" \
  SPIN_TREE_pytest__coverage_opts="[{python.version}]" \
    spin -p pytest.opts="[{python.version}]" --dump | grep -A4 "|pytest:"
  src/spin/cli.py:142:            |pytest:
  command-line:0:                 |  opts:
                                  |    - 3.11
  command-line:0:                 |  coverage_opts:
                                  |    - 3.11
