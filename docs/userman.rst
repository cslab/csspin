==========
Using Spin
==========

Spin, or better the spin plugins, do just two things: they provision
development environments, and run development tools.

.. index::
   single: environment

An **environment** is a directory, where spin creates language stack
specific things, e.g. for Python it creates a virtual
environments. Then, the project's runtime and development dependencies
and the project itself are installed into the
environment. Environments must be created explicitly, by passing the
command line option :option:`--provision <spin --provision>` to
spin. Spin will refuse to run most tasks before an environment has
been created.

Environments are generally created *outside* the source tree, in
:file:`$XDG_CACHE_HOME/spin`. Spin plugins try hard to place
everything that is generated while building, testing etc. in the
environment directory, to keep the source tree clean.

**Tasks** are commands run by spin plugins inside an environment,
e.g. the Python plugin registers a :program:`python` task, that
simply runs the Python interpreter.

.. index::
   single: workflow

**Workflows** are tasks that run *other* tasks. This can be used to
abstract from specific tools and stacks: the :program:`test` workflow
runs :program:`pytest`, when the project uses `pytest`_, but
:program:`nosetests`, when the project uses `nosetests`_. When a
project also uses Javascript, :program:`test` might also run
:program:`jest`.

Workflows can also combine tools and other workflows: the
:program:`preflight` workflow runs tests and lints and checks all
changed files.


Writing ``spinfile.yaml``
=========================

Spin expects a `YAML <https://yaml.org/>`_ file named
``spinfile.yaml`` in the top-level folder of the project that lists
the plugins to use, parameters for task etc. This file is used to
construct a *configuration tree*, a nested data structure that defines
the project and the behavior of the task plugins. The configuration
tree is built from (in this order):

* The default configuration of each plugin and spin itself. E.g. the
  ``flake8.cmd`` setting has a default value of ``"flake8"`` that is
  set by the plugin :py:mod:`spin.builtin.flake8`. This setting is
  used to construct the command line to call ``flake8``.
* The settings from ``spinfile.yaml`` complement (or override) the
  defaults.
* If it exists, user-specific settings are read from
  ``$XDG_CONFIG_HOME/spin/global.yaml`` and complement the project
  configuration tree; an example for a user-specific setting is
  ``devpi.host``, the host name of a devpi package server.
* Command line settings given by :option:`-p prop=value <spin -p>`
  override all other settings; a typical use case is to override the
  version of the Python interpreter using ``spin -p
  python.use=python3.7`` in a CI build to avoid provisioning a Python
  interpreter on each run.


Each spinfile must have at least :py:data:`minimum-spin`, to state the
oldest version of spin that can process the file. To do anything
useful, at least one plugin must be included. Here, we use the Python
plugin, that also requires a version.

.. code-block:: yaml

   minimum-spin: 0.2.dev

   plugins:
     - spin.builtin.python

   python:
     version: 3.9.6

You can visualize the configuration tree for this minimal example by
using the :option:`--debug <spin --debug>` option (many lines left
out):

.. code-block:: console
   :emphasize-lines: 4,9,10,12

   $ spin --debug
   spin: cd /home/me/myproj
   spin: set PYENV_VERSION=3.9.6
   spinfile.yaml:1:                       |minimum-spin: '0.2.dev'
   ~/spin/src/spin/schema.yaml:19:        |spin:
   ~/spin/src/spin/cli.py:528:            |  spinfile: Path('/home/me/myproj/spinfile.yaml')
   ~/spin/src/spin/schema.yaml:36:        |  env_base: '{spin.userprofile}/{spin.project_hash}'
   ... more lines ...
   spinfile.yaml:3:                       |plugins:
					  |  - 'spin.builtin.python'
   ~/spin/src/spin/builtin/python.py:91:  |python:
   spinfile.yaml:7:                       |  version: '3.9.6'
   ... even more lines ...

:option:`--debug <spin --debug>` shows the complete configuration
tree, and for each setting, where it came from. The highlighted lines
are from the project spinfile, while the rest are spin's default
settings.

There are dozens of settings defined by the spin framework, and each
plugin comes with its own set of settings and uses settings from other
plugins and the framework.


Importing Plugins
-----------------

Plugins are Python modules, and they are imported by spin using their
(full) import name. Plugin import names are listed under the
:py:data:`plugins` key. It is important to note, that plugin modules
and spin itself are totally separate from your project, even it uses
Python. Spin's builtin plugins live in the :py:mod:`spin.builtin`
namespaces. The example below imports four plugins:

.. code-block:: yaml

   plugins:
     - spin.builtin.python
     - spin.builtin.flake8
     - spin.builtin.pytest

To not repeat yourself, this can be expressed more compact by nesting
the plugins under some namespaces. The next example is equivalent to
the previous one:

.. code-block:: yaml

   plugins:
     - spin.builtin:
       - python
       - flake8
       - pytest


Local Plugins
-------------

Spin supports project-specific plugins local to a project. You can
specify a list of paths relative to the root directory of the project,
where spin looks for local plugins using the ``plugin-path`` key:

.. code-block:: yaml

   plugin-path:
     - plugins/deployment
     - plugins/distros

   # Assuming pluginA.py is in of those directories, it can now be
   # loaded
   plugins:
     - pluginA
     - ...


Shared Plugins
--------------

Shared plugins are intended to be used by many different
projects. They are distributed as Python packages, and can be
installed from a package server or a Git repository.  Plugin packages
can be listed under the ``plugin-packages`` key as pip-compatible
dependency specifiers:

.. code-block:: yaml

   plugin-packages:
     - someones-spin-plugins~=2.0
     - git+https://git.example.com/projstds#egg=projstds

Spin will install plugin packages into :file:`{spin.env_base}/plugins`
(where *spin.env_base* is a setting from the configuration tree).


Interpolation
-------------

Settings in the configuration tree can refer to other settings by
using *string interpolation*: path expressions surrounded by braces
are replaced by the setting given. E.g. ``{spin.project_root}`` is the
setting ``project_root`` in the subtree ``spin`` and its semantic is
to hold the path of root directory of the project (i.e. where
``spinfile.yaml`` is located). Strings are interpolated until they no
longer contain an expression. Expressions are resolved recursively so
an interpolation can result in another interpolatable expression, that
will be interpolated as well, until the process reaches its fix point.

In YAML, braces are syntactical meta-characters that indicate a
literal dictionary (like in JSON, of which YAML is
super-set). Settings using string interpolation must therefore be
quoted. Example:

.. code-block:: yaml

   devpi:
      user: frank
      url: http://haskell:4033
      stage: "{devpi.url}/{devpi.user}/staging"


Extra Tasks
-----------

If a project needs a few extra tasks, those can be defined explicitly
in spinfile using ``extra-tasks``: for each new task a key is added,
and each task can define the following sub-keys:

* ``script``: a list of shell commands
* ``env``: a dictionary of environment variables, that should be set
  when running the shell commands
* ``spin``: a list of spin commands (without ``spin``)
* ``help``: help text to display

The following example adds ``pipx-install`` and ``all`` as tasks to
spin:

.. code-block:: yaml

   extra-tasks:
     pipx-install:
       env:
	 USE_EMOJI: no
       script:
	 - pipx install --force --editable .
       help: |
	 This installs spin via pipx

     all:
       spin:
	 - build
	 - tests
	 - docs
	 - package
	 - upload


Build Rules
-----------

Spin has a *very* simple built-in facility for automatically
generating target files depending on source files -- similar to Unix
Make, although *much* more primitive. Don't use this to simulate a
real build tool!

Dependencies are declared under the ``build-rules`` key as follows:

* each subkey is a target; tasks are "pseudo" targets prefixed with
  ``"task "`` (exactly one space!)

* each target can have the following keys:

  * ``sources``: a path or a list of paths that are inputs for the
    target

  * ``script``: a list of shell commands that are executed to re-build
    the target if necessary

  * ``spin``: a list of spin tasks that are executed to re-build the
    target if necessary

.. todo:: This should support ``env`` as well!

Here is an example from a previous version of the spin project
itself.

**Example 1**: The reference documentation for the spinfile schema is generated from
a schema file by a spin task. The resulting :file:`docs/schemaref.rst`
is updated whenever :program:`spin docs` is executed, and
:file:`src/spin/schema.yaml` is more recent than
:file:`schemaref.rst`:

.. code-block:: yaml

   build-rules:
     task docs:
       sources: docs/schemaref.rst
     docs/schemaref.rst:
       sources: [src/spin/schema.yaml]
       spin:
	 - schemadoc -o docs/schemaref.rst



Plugins
-------

Spin by itself does nothing. All tasks are defined in *plugins*. Spin
plugins are Python modules. A plugin can do one or more of the
following:

* register new subcommands; e.g. the **lint** plugin registers a
  subcommand ``lint``; this can be verified by calling ``spin
  --help``, which displays all know subcommands.

* declare plugin dependencies, e.g. the **flake8** plugin depends on
  the **lint** and **python** plugins. **lint** is required, because
  **flake8** registers itself as a linter for the project. **python**
  is required because we need Python to actually run
  :program:`flake8`.

* declare package requirements, that are installed into a virtual
  environment. For example, the **flake8** plugin requires
  :program:`flake8` and some of its extensions to be installed.

* declare *hooks* that are called while spin runs; e.g. the
  **python** plugin declares a hook that provisions the required
  Python release.

System Dependencies
-------------------

.. todo:: This feature is functional, but not yet complete!

Spin allows projects to define system dependencies. These are
dependencies that can not be provisioned by spin locally to the
project, but must be installed to the machine running spin by a system
package manager (e.g. :program:`apt` on Debian Linux) or installation
scripts. This mechanism is also used by plugins to support
provisioning the host to support their particular function. For
example, the Python plugin on Linux declares system dependencies that
enable building Python from source.

Installing system dependencies requires administrative access to
the machine (e.g. :program:`sudo`). Spin's :program:`system-provision`
task therefore simply generates a script that is to be executed via an
elevated shell:

.. code-block:: console

   $ spin system-provision | sudo sh

Package names and installation commands for system dependencies vary
between operating systems and distributions. Declaring system
dependencies therefore uses simple Python conditions to choose between
different sets of packages: spin feeds variables named
:py:data:`distro` and :py:data:`version` to the conditions, and each
matching condition contributes to the set of packages to install.

System dependencies are declared under the key
:py:data:`system-requirements`. The following sample would generate an
installation command for :program:`libaio1` and :program:`gettext` on
Debian systems.

.. code-block:: yaml

   system-requirements:
     distro=="debian":
       apt-get: libaio1 gettext

Provisioning the project on a host running Debian would generate a
script that looks like so (note all the other dependencies that are
coming from plugins used by the project):

.. code-block:: console

   $ spin system-provision
   spin: cd /home/me/myproj
   spin: set PYENV_VERSION=3.11.2
   apt-get update
   apt-get install -y git make build-essential libssl-dev zlib1g-dev \
           libbz2-dev libreadline-dev libsqlite3-dev curl
	   libncursesw5-dev \
	   xz-utils libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
	   libaio1 gettext

Once a project has system requirements defined, spin will generate an
error message if provisioning is attempted on another platform:

.. code-block:: console

   $ spin system-provision fedora
   spin: cd /home/frank/spin
   spin: set PYENV_VERSION=3.11.2
   spin: error: this project does not support fedora
   Aborted!

The system provisioning feature can be used to conveniently and
repeatably prepare developer workstations or Docker containers for
working with a project.

Distro names come from the ``distro`` package
(https://github.com/python-distro/distro). For Windows, the distro
name is ``"windows"`` and ``version`` will be set to the major, minor
and build number of Windows.


Sample ``global.yaml``
======================

``spin`` looks for a file called ``global.yaml`` in
``$XDG_CONFIG_HOME/spin``. Settings from this file are merged into the
project configuration tree. This facility can be used to provide
user/machine specific settings like in the example below.

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

   # The 'devpackages' key defines mappings from dependency names to
   # actual pip specs. This can be used like below to install certain
   # packages from local sandboxes or elsewhere instead from the package
   # server used.
   devpackages:
     cpytoolchain: "-e {HOME}/Projects/cpytoolchain"


.. hyperlinks

.. _pytest: https://pytest.org/
.. _nosetests: https://nose.readthedocs.io/
