==========
About spin
==========

Spin is a task runner that aims so solve the problems of
**provisioning development environments** and **standardizing
workflows**.

Spin automates the provisioning of tools and other development
requirements (including language stacks like Python,
Javascript/Node). As an example, for a project that uses Python and
Javascript `spin` would:

* provision the requested version of Python
* provision the requested version of Node
* create a virtual development environment, where the required
  versions of Python and Node can be used
* install tools for linting and testing etc.
* install pre-commit and install the git hooks

All with a single command: ``spin --provision``!

Second, `spin` standardizes workflows, best practices and how
development tools are used, especially in environments with many
similar projects that share practices and tools. For a typical Python
project the command ``spin preflight`` would:

* automatically run installed linters like :program:`flake8`
* run tests using :program:`pytest`

By default, `spin` will automatically generate the right options and
arguments for the tools it runs, and show the user the precise
commands.

Built-in workflows include ``build``, ``lint`` and ``tests`` (all
three will be run by ``preflight``), as well as ``bump-version``,
``package``, ``upload``, ``deploy`` etc. -- workflows are also
extensible by plugins.

As a result, *anyone* will be able to check out *any project*, do
``spin --provision`` and will be all set. Running a project's test
suite becomes as simple as doing ``spin test`` etc.


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
stacks: it is just a slick way to store and re-use definitions for
installing software and running other programs to make it easy for
developer to work with projects.


Is it necessary to run everything via spin?
-------------------------------------------

Absolutely not! `spin` intentionally echoes the commands it runs, to
make the user understand what is going on. It also patches or provides
activation scripts for development environments, to enable users to
"switch" to an environment provisioned by spin, and run the commands
manually. Spin plugins try to be well-behaved in this regard, and do
not silently modify the environment, to make everything that is going
on transparent to the user.


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

`spin` has a library of built-in plugins for Python, Node, Java,
C/C++ and common tools in those stacks. It's also easy to add plugins
local to a project, or shared plugins that live as Python packages on
some Python package server or a Git repository.


Project Settings and :file:`spinfile.yaml`
==========================================

The choice of plugins to use, and other project-specific settings go
into a file called :file:`spinfile.yaml` in your project's root
directory. As an example, the most simple Python project would have a
:file:`spinfile.yaml` looking like so:

.. code-block:: yaml

   minimum-spin: 0.2
   plugins:
     - spin.builtin.python
   python:
     version: 3.9.6

Provisioning this project would install Python 3.9.6 and create a
virtual environment for working with the project:

.. code-block:: console

   $ spin --provision
   spin: cd /home/me/myproj
   spin: set PYENV_VERSION=3.9.6
   spin: python --version
   Python 3.9.6
   spin: python -mpip -q install -U virtualenv packaging
   spin: activate /home/me/myproj/cp38-manylinux_2_28_x86_64
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
   spin: activate /home/me/myproj/cp38-manylinux_2_28_x86_64
   spin: pip -q install -e .
   spin: pip -q install pytest

Also, `spin` gained a new subcommand ``spin pytest``:

.. code-block:: console

   $ spin pytest
   spin: cd /home/me/myproj
   spin: set PYENV_VERSION=3.9.6
   spin: activate /home/me/myproj/cp38-manylinux_2_28_x86_64
   spin: /home/me/myproj/cp38-manylinux_2_28_x86_64/bin/pytest  ./tests
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
makes spin simply import and use the plugin module
``mycompany.projstds``.

Your team's :program:`projstds` plugin comes with lots tools and
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
   spin: activate /home/me/myproj/cp38-manylinux_2_28_x86_64
   spin: pip -q install -e .
   spin: pip -q install pytest pre-commit flake8 black flake8-isort ...
   spin: pre-commit install
   pre-commit installed at .git/hooks/pre-commit

This is a basic pattern working with spin: you modify your environment
by editing :file:`spinfile.yaml` and ask spin to re-provision the
environment.

========
Examples
========

Here are examples from spin itself.

* Run spin's test suite:

  .. code-block:: console

     $ spin tests
     spin: cd /Users/frank/Projects/spin
     spin: set PATH=/Users/frank/Projects/spin/cp38-macosx_10_15_x86_64/bin:$PATH
     spin: ./cp38-macosx_10_15_x86_64/bin/pytest --cov=spin --cov=tests --cov-report=html ./tests
     .........
     ------------------------------------------------------------------------------
     Ran 9 tests in 1.10s

     ---------- coverage: platform darwin, python 3.8.1-final-0 -----------
     Coverage HTML written to dir htmlcov


     OK

* Run preflight checks. This includes the tests, and also runs
  available linters.

  .. code-block:: console

     $ spin preflight
     spin: cd /Users/frank/Projects/spin
     spin: ./cp38-macosx_10_15_x86_64/bin/pytest --cov=spin --cov=tests --cov-report=html ./tests
     ........
     ------------------------------------------------------------------------------
     Ran 8 tests in 0.42s

     ---------- coverage: platform darwin, python 3.8.1-final-0 -----------
     Coverage HTML written to dir htmlcov


     OK
     spin: flake8 --exit-zero tests/test_cruise.py tests/test_flake8.py
     spin: radon mi -n B tests/test_cruise.py tests/test_flake8.py


Overview
========


Plugins
-------

Spin by itself does nothing. All tasks are defined in *plugins*.
Plugins have to be declared in ``spinfile.yaml`` using the ``plugins``
key, for example::

  plugins:
    - flake8
    - pytest

A plugin can do one or more of the following:

* register new subcommands; e.g. the **lint** plugin registers a
  subcommand ``lint``; this can be verified by calling ``spin
  --help``, which displays all know subcommands

* declare plugin dependencies, e.g. the **flake8** plugin depends on
  the **lint** and **virtualenv** plugins. **lint** is required,
  because **flake8** registers itself as a linter for the
  project. **virtualenv** is required because we need virtual
  environment to install the actual ``flake8`` package from PyPI.

* declare package requirements, that are installed into a virtual
  environment

* declare *hooks* that are called while spin runs; e.g. the
  **python** plugin declares a hook that provisions the required
  Python release


The Configuration Tree
----------------------

Spin expects a `YAML <https://yaml.org/>`_ file named
``spinfile.yaml`` in the top-level folder of the project that declares
tasks, dependencies etc. This file is used to construct a
*configuration tree*, a nested data structure that defines the project
and the behavior of the task plugins. The configuration tree is built
from (in this order):

* the default configuration of each plugin and spin itself. E.g. the
  ``flake8.cmd`` setting is ``"flake8"``. This setting is used to
  construct the command line to call ``flake8``.
* the settings from ``spinfile.yaml`` complement (or override) the
  defaults
* if it exists, user-specific settings are read from
  ``~/.spin/global.yaml`` and complement the project configuration
  tree; an example for a user-specific setting is ``devpi.stage``, the
  staging index for uploading packages
* command line settings given by ``-p prop=value`` override all other
  settings; a typical use case is setting the python interpreter to
  use with ``spin -p python.use=python3.7`` etc.

Settings in the configuration tree can refer to other settings by
using *string interpolation*: path expressions surrounded by braces
are replaced by the setting given. E.g. ``{spin.project_root}`` is the
setting ``project_root`` in the subtree ``spin`` and its semantic is
to hold the relative path of root directory of the project (i.e. where
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

There are dozens of settings defined by the spin framework, and each
plugin comes with its own set of settings and uses settings from other
plugins and the framework.


Why YAML?
---------

Good question. To me it seemed like the choice that sucked least. It
has comments, it is well supported by text editors, and its data model
blends naturally with the configuration tree paradigm of spin. YAML
has the same information model as JSON: supported data types include
dictionaries, lists and literals (mostly strings).

However, YAML is a complex beast. You can do all kinds of mischievous
tricks with YAML, and if you mess up the tree, the ``spin`` command
will most likely fail to run.



Built-in Plugins
----------------

Spin comes with a set of built-in plugins:

* **python** -- provision Python by using a pre-existing Python
  installation or automatically install the requested Python release
* **virtualenv** -- provision a virtualenv in the project directory
  and add required packages to that
* **lint** -- provide subcommand ``lint`` that runs linters
* **flake8**
* **radon**
* **devpi** -- provide the subcommand ``stage`` to upload the package
  to a devpi staging index
* **git** -- git support
* **pytest** -- use pytest for Python tests
* **test** -- provide subcommand ``tests`` that runs automatic tests


Workflows
---------

Workflows are simply plugins that trigger tasks from other
plugins. **lint** is a simple workflow that launches all linters set
for the project. Another workflow is **preflight** that runs tests and
lint checks.

We plan to add things similar (and better) than those in the driver
``Makefile`` currently used for `cs.platform` (**to be completed**).


Cruising
--------

Spin supports running itself in one or many docker containers (and
maybe elsewhere in the future). This is called *cruising*, and it is
useful to validate projects from a development sandbox for different
platforms. The ``spinfile.yaml`` of the spin project itself defines
the following cruises:

.. code-block:: yaml

   cruise:
     "@docker":
       # The docker containers are set up to have 'python' in PATH as the
       # Python version they announce in their name.
       properties:
         python.use: python
     windows:
       image: registry.contact.de/cp38-win_amd64
       tags: docker windows
       cruise_spin: devrun.bat
     linux:
       image: registry.contact.de/cp38-manylinux2014_x86_64
       tags: docker linux
       cruise_spin: ./devrun.sh
     host:
       tags: host

The ``properties`` setting in the ``@docker`` subtree sets the command
line option ``-p python.use=python`` for all Docker containers. This
is useful as spin otherwise would provision a Python installation
inside the container, which is unnecessary because the images used are
already prepared to have the required Python release.

This set includes docker images for Windows as well as Linux, which
means we need to have one docker daemon available for each
platform. These are defined as user-specific settings in
``$HOME/.spin/global.yaml``:

.. code-block:: yaml

   cruise:
     "@windows":
       context: winsrv2019
       volprefix: "c:"
     "@linux":
       context: default

Each "cruise" is defined by merging its settings with all settings
from matching tags. I.e. a cruise tagged with ``windows`` will inherit
the configuration from the ``@windows`` key.


Cruises are selected by using the ``-c`` (or ``--cruise``) option to
``spin``. The following will run spin in the Linux container.

.. code-block:: console

   $ spin -c linux <whatever> ...

Cruises can also be selected by specifying tags (which are prefixed by
``"@"``). This will run all Docker containers:

.. code-block:: console

   $ spin -c @docker <whatever> ...

A special selector is ``@all``, selecting all cruises. In spin's case
this means running the requested task for all supported platforms.


Example
=======

The following shows an invocation of ``spin lint`` when nothing has
been provisioned yet.

.. code-block:: console

   $ spin lint --all
   spin: cd /Users/frank/Projects/spin


The project requires Python 3.8.1 which is provisioned by the
**python** plugin using ``python-build`` from the ``pyenv``
distribution (on Windows **python** would use ``nuget``).

.. code-block:: console

   spin: Installing Python 3.8.1 to /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1
   spin: set PYTHON_BUILD_CACHE_PATH=/Users/frank/.spin/cache
   spin: /Users/frank/.spin/pyenv/plugins/python-build/bin/python-build 3.8.1 /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1
   python-build: use openssl@1.1 from homebrew
   python-build: use readline from homebrew
   Installing Python-3.8.1...
   python-build: use readline from homebrew
   python-build: use zlib from xcode sdk
   Installed Python-3.8.1 to /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1
   spin: /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1/bin/python -m pip install -q --upgrade pip wheel
   spin: /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1/bin/python -m pip install virtualenv


Next, the **virtualenv** plugin creates a virtual environment in the
project directory and installs all packages required by the project
(via the ``requirements`` key in ``spinfile.yaml``), or by the plugins
used.

.. code-block:: console

   spin: /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1/bin/python \
	 -m virtualenv -q \
	 -p /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1/bin/python \
	 ./cp38-macosx_10_15_x86_64
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install radon
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install pytest
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install pytest-cov
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install pytest-tldr
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install flake8
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install flake8-fixme
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install flake8-import-order
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install flake8-comprehensions
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install flake8-copyright
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install flake8-bugbear
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install devpi-client
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install keyring

If the project has a ``setup.py`` it is installed into the virtual
environment in development mode:

.. code-block:: console

   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install -e .


Finally, ``spin`` modifies ``PATH`` to include the virtual environment
and launches all linters declared for this project (``flake8`` and
``radon`` in this case).


.. code-block:: console

   spin: set PATH=/Users/frank/Projects/spin/cp38-macosx_10_15_x86_64/bin:$PATH
   spin: flake8 ./src ./tests
   spin: radon mi -n B ./src ./tests


Invoking the same command a second time will naturally not
re-provision everything, but simply launch the linters:

.. code-block:: console

   $ spin lint --all
   spin: cd /Users/frank/Projects/spin
   spin: set PATH=/Users/frank/Projects/spin/cp38-macosx_10_15_x86_64/bin:$PATH
   spin: flake8 ./src ./tests
   spin: radon mi -n B ./src ./tests

Note that dependencies are taken care off automatically. Adding

.. code-block:: yaml

   requirements:
      - flake8-docstrings

to ``spinfile.yaml`` will automatically add the requested package to
the virtual environment:

.. code-block:: console

   $ spin lint --all
   spin: cd /Users/frank/Projects/spin
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install flake8-docstrings
   spin: set PATH=/Users/frank/Projects/spin/cp38-macosx_10_15_x86_64/bin:$PATH
   spin: flake8 ./src ./tests
   ./src/spin/cruise.py:15:1: D103 Missing docstring in public function
   ./src/spin/cruise.py:25:1: D103 Missing docstring in public function
   ./src/spin/cruise.py:39:1: D103 Missing docstring in public function
   ... and so on ...


Simply removing the ``requirements`` setting from ``spinfile.yaml``
will not remove that package, though. We can either simply remove that
environment, or use ``spin exec`` to run ``pip`` inside the
environment:

.. code-block:: console

   $ spin exec pip uninstall flake8-docstrings



Reference
=========

Where files go
--------------

* ``$HOME/.spin/`` -- Python releases and configuration files that are
  not project-specific

* ``<project_root>/.spin`` -- plugin packages and project-specific
  settings

* ``<project_root>/<venv>`` -- platform/ABI specific virtual
  environment (provisioned by the built-in plugin *virtualenv*)



Sample ``global.yaml``
======================

``spin`` looks for a file called ``global.yaml`` in
``~/.spin``. Settings from this file are merged into the project
configuration tree. This facility can be used to provide user/machine
specific settings like in the example below.

.. code-block:: yaml

   # Settings for frank@haskell

   # Cruise needs different docker contexts for Windows and Linux
   # containers. This way, my (machine-specific) settings get merged into
   # cruise definitions for project-specific containers.
   cruise:
     "@windows":
       context: winsrv2019
       volprefix: "c:"
     "@linux":
       context: default

   # I use a local devpi mirror. Set its properties here.
   devpi:
     user: frank
     url: http://haskell:4033
     stage: "{devpi.url}/{devpi.user}/staging"

   # Override pipconf settings in virtualenv to use my devpi mirror.
   virtualenv:
     pipconf:
       global:
         extra-index-url: "{devpi.stage}/+simple/"

   # The 'devpackages' key defines mappings from dependency names to
   # actual pip specs. This can be used like below to install certain
   # packages from local sandboxes or elsewhere instead from the package
   # server used.
   devpackages:
     cpytoolchain: "-e {HOME}/Projects/cpytoolchain"


Understanding the Configuration Tree
====================================

The ``--debug`` option makes ``spin`` dump the configuration tree
annotated with the places settings came from. Example:


.. code-block:: console

   $ spin --debug test
   spinfile.yaml:1:     plugins:
                          - 'flake8'
                          - 'pytest'
                          - 'devpi'
                          - 'git'
                          - 'radon'
   spinfile.yaml:10:    cruise:
   spinfile.yaml:11:      @docker:
   spinfile.yaml:14:        opts:
		              - '-p'
                              - 'python.use=python'
   src/spin/cli.py:38:      executor: <class 'spin.cruise.DockerExecutor'>
   spinfile.yaml:15:      cp27-win:
   spinfile.yaml:16:        banner: 'Manylinux Container with Python 2.7 on Windows'
   spinfile.yaml:17:        image: 'registry.contact.de/cp27m-win_amd64'
   spinfile.yaml:18:        tags:
                              - 'docker'
                              - 'windows'
   spinfile.yaml:14:        opts:
		              - '-p'
                              - 'python.use=python'
   src/spin/cli.py:38:      executor: <class 'spin.cruise.DockerExecutor'>
   ~/.spin/global.yaml:8:   context: 'winsrv2019'
   ~/.spin/global.yaml:9:   volprefix: 'c:'
   ...
