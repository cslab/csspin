:category: README
:author: Frank Patz-Brockmann
:link_pdf:

======
 spin
======

Spin is a task runner that aims so solve the problem of standardizing
workflows for many similar projects. It does this by encapsulating
task definitions in Python packages and automating the provisioning of
development sandboxes and dependencies.

.. toctree::

   README

Installation
============

Basic information:

* Spin requires Python 3.8
* it is currently under development, pull often
* it's most convenient to have the ``spin`` command available on your
  ``PATH``

We currently recommend to install spin directly from its cloned
repository using `pipx
<https://pipxproject.github.io/pipx/>`_. ``pipx`` is a tool that
installs Python packages into a user-specific location in a user's
``HOME`` directory.

Install ``pipx``:

.. code-block:: console

   $ python38 -m pip install --user pipx
   $ python38 -m pipx ensurepath

``ensurepath`` adds ``$HOME/.local/bin`` to your shell's
configuration, so commands from packages installed by ``pipx`` are
available in ``PATH``. Make sure to restart your shell to make the
setting effective.

Use ``pipx`` to install spin:

.. code-block:: console

   $ git clone git@git.contact.de:frank/spin.git
   $ cd spin
   $ pipx install --editable .

The ``spin`` command is now available in your ``PATH``, linked to your
clone of the spin repository. Updating the repository will
automatically give you the most up-to-date code.


Usage
=====

``spin`` provides subcommands that normally simply call other
tools::

  spin [OPTIONS] COMMAND [ARGS]...

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


Developing Plugins
------------------

Plugins are Python modules that are imported by ``spin``, doing
whatever side-effects are required. Plugins are loaded in one the
following three ways:

* plugins that are listed under the ``plugins`` key of ``spinfile.yaml``

* plugins that are listed as requirements in another plugin's
  configuration subtree under the ``requires`` key

* lastly, ``spin`` loads all plugins registered as Python
  *entry points* in the ``spin.plugin`` group automatically; this is
  useful for plugins that provide globally available commands which
  are not specific to a particular project; plugins meant to be used
  in the context of a project do not provide entry points for automatic
  loading.


The API of plugins consists of the following:

* an optional module-level variable ``defaults`` holding a
  configuration subtree created by the `config()`; this configuration
  tree will be merged with project and global settings and become the
  configuration subtree named like the plugin

* an optional ``init(cfg)`` callback that is called before any
  subcommand is executed; ``init`` can be used to provision
  dependencies, e.g. the **python** plugin provisions a Python
  interpreter in its ``init``

* an optional ``cleanup(cfg)`` callback that is called when running
  ``spin cleanup``; this is used to unprovision dependencies, e.g. the
  **python** plugin removes the installation tree of the Python
  interpreter it provided it ``init`` callback

* an optional ``configure(cfg)`` callback that is called before
  ``init``; here, plugins can manipulate the configuration tree so
  that subsequent callbacks of other plugins behave differently

Callbacks are called in "dependency" order, i.e. the plugin dependency
graph (as given by ``requires``) is topologically sorted.


Further, importing a plugin can have side-effects like adding
subcommands to ``spin`` by using the decorators ``@task`` and
``@group``.

Here is an example for a simple plugin:

.. code-block:: python

   # We assume that this plugin module is called `example`, providing
   # a subcommand of the same name.

   from spin import config, echo, task

   defaults = config(msg="This projects lives in {spin.project_root}")

   @task()
   def example(cfg):
       """Example plugin"""
       echo(cfg.example.msg)

To activate this plugin, it has to be declared in ``spinfile.yaml``:

.. code-block:: yaml

   # spinfile.yaml
   plugins:
     - example   # assuming 'example' is available somewhere in sys.path

By this ``spin`` gains a new subcommand ``example`` which we can use
to print our message:

.. code-block:: console

   $ spin --help
   ...
   Commands:
   ...
     example    Example plugin
   ...
   $ spin example
   spin: This project lives in .



Plugin API
----------

The API for plugin development is defined in ``spin`` (sorry,
documentation pretty incomplete right now). The general idea is to
keep plugin scripts short and tidy, similar to shell scripts of
commands in a Makefile. Thus, ``spin`` provides simple, short-named
Python function to do things like manipulating files and running
programs.

Arguments to spin APIs are automatically interpolated against
the configuration tree.

.. py:function:: cd(path)

   Change the current working directory to `path`, which is
   interpolated against the configuration tree. `cd` can be used as a
   context manager using ``with``, in that case it changes the working
   directory back to the original one when the ``with`` clause ends.


.. py:function:: config(**kwargs)

   `config` creates a configuration subtree::

     >>> config(a="alpha", b="beta)
     {"a": "alpha", "b": "beta")

   Plugins use `config` to declare their ``defaults`` tree.


.. py:function:: die(*msg)

   Terminates ``spin`` with a non-zero return code and print the error
   message `msg`. Arguments are interpolated against the configuration
   tree.


.. py:function:: echo(*msg, **kwargs)

   Print a message to the console by joining the positional arguments
   `msg` with spaces. Arguments are interpolated against the
   configuration tree. `echo` will remain silent when ``spin`` is run
   with the ``--quiet`` flag.

   `echo` supports the same keyword arguments as Click's
   :py:func:`click.echo`.


.. py:function:: exists(path)

   Checks whether `path` exists. `path` is interpolated against the
   configuration tree.


.. py:function:: mkdir(path)

   Ensures that the directory hierarchy `path` exist, creating
   directories if necessary. The argument is interpolated against the
   configuration tree.


.. py:function:: rmtree(path)

   Recursively removes the directory `path`. The argument is
   interpolated against the configuration tree.


.. py:function:: sh(*cmd, silent=False, shell=False, **kwargs)

   Run a program by building a command line from `cmd`. When multiple
   positional arguments are given, each is treated as one element of
   the command. When just one positional argument is used, `sh`
   assumes it to be a single command and splits it into multiple
   arguments using `shlex.split`. The `cmd` arguments are interpolated
   against the configuration tree. When `silent` is ``False``, the
   resulting command line will be echoed. When `shell` is ``True``,
   the command line is passed to the system's shell. Other keyword
   arguments are passed into `subprocess.run`.


.. py:class:: Command(*cmd)

   Wraps a partial command into a callable object. Arguments given to
   the new callable will be appended to the wrapped command. Example::

   >>> pipinstall = Command("pip", "-q", "install")
   >>> pipinstall("flake8")


.. py:function:: setenv(**kwargs)

   Manipulate environment variables. Assigning ``None`` will remove
   the environment variable. Argument values are interpolated against
   the configuration tree.


.. py:function:: read[text|bytes](fn)

   `readtext` reads an UTF8 encoded text from the file
   'fn'. `readbytes` reads binary data. The file name argument is
   interpolated against the configuration tree.


.. py:function:: write[text|bytes](fn, data)

   Write `data`, which is either text (Unicode object of type `str`)
   or binary data (`bytes`) from the file named `fn`. The file name
   argument is interpolated against the configuration tree.

.. py:class:: Memoizer(fn)

   The `Memoizer` class stores and retrieves Python objects from the
   binary file named `fn`. The argument is interpolated against the
   configuration tree. `Memoizer` can be used to keep a simple
   "database". Spin internally uses Memoizers for e.g. keeping track
   of packages installed in a virtual environment.

   To ease the handling in `spin` scripts, there also is context
   manager called `memoizer` (note the lower case "m"). The context
   manager retrieves the database from the file and saves it back when
   the context is closed::

     >>> with memoizer(fn) as m:
     ...    if m.check("test"): ...

   There are *no* precautions for simultaneous access from multiple
   processes, writes will likely silently become lost.

   .. py:method:: check(item)

      Checks whether `item` is stored in the memoizer.

   .. py:method:: items()

      Returns the list of items in the memoizer.

   .. py:method:: add(item)

      Add `item` to the memoizer.

   .. py:method:: save()

      Persist the current state of the memoizer. This is done
      automatically when using `memoizer` as a context manager.


.. py:function:: task([name,] *args, *, when, aliases, **clickargs)

   Decorator that creates a task. This is a wrapper around Click's
   `click.command` decorator, with some extras:

   * a string keyword argument `when` adds the task to the list of
     commands to run using `invoke`
   * `aliases` is a list of aliases for the command (e.g. "check" is
     an alias for "lint")
   * `task` introspects the signature of the decorated function and
     handles certain argument names automatically:

     * ``ctx`` will pass the Click context object into the task; this
       is rarely useful for spin tasks
     * ``cfg`` will automatically pass the configuration tree; this
       very useful most of the time, except for the simplest of tasks
     * ``args`` will simply pass through all command line arguments by
       using the ``ignore_unknown_options`` and ``allow_extra_args``
       options of the Click context; this is often used for tasks that
       launch a specific command line tool to enable arbitrary
       arguments

   All other arguments to the task must be annotated with either
   `option` or `argument`. They both support the same arguments as the
   corresponding decorators `click.option` and `click.argument`.

   A simple example:

   .. code-block:: python

      @task()
      def simple_task(cfg, args):
          # do something

   This would make ``simple_task`` available as a new subcommand of
   spin.

   More elaborate examples can be found in the built-in plugins
   shipping with spin.


.. py:function:: invoke(hook, *args, **kwargs)

   ``invoke()`` invokes the tasks that have the ``when`` hook
   `hook`. As an example, here is the implementation of **lint**:

   .. code-block:: python

     @task(aliases=["check"])
     def lint(allsource: option("--all", "allsource", is_flag=True)):
         """Run all linters defined in this project."""
	 invoke("lint", allsource=allsource)

   Note that in this case, all linters are required to support the
   ``allsource`` argument, i.e. the way a task that uses `invoke` is
   invoking other tasks is part of the call interface contract for
   linters: *all* linter tasks *must* support the ``allsource``
   argument as part of their Python function signature (albeit not
   necessarily the same command line flag ``--all``).


Others (not yet really documented):

* ``persist()`` and ``unpersist()`` read and write Python objects
  from/to the file system
* ``download()`` downloads something to disk
* ``get_tree()`` gets the global configuration tree (which may be
  necessary sometimes when it is not passed into a plugin hook by spin
  automatically)


Here is a simple example of using the spin API:

.. code-block:: python

   from spin import cd, die, echo, exists, sh

   def meaningless_example():
       echo("This project is located in {spin.project_root}")
       with cd("{spin.project_root}"):
           # We can pass each argument to a command separately,
	   # which saves us from quoting stuff correctly:
	   sh("ls", "-l", "spinfile.yaml")

	   # We can also simply use whole command lines:
	   sh("echo {spin.project_root} > project_root.txt")

       if not exists("project_root.txt"):
	   die("I didn't expect that!")


Using spin programmatically
---------------------------

.. py:function:: main(*cmd)

   Run ``spin`` from a program, propagating exception etc.

   Example:

   .. code-block:: pycon

      >>> import spin
      >>> spin.main("lint", "--all")
      spin: cd /Users/frank/Projects/spin
      spin: set PATH=/Users/frank/Projects/spin/cp38-macosx_10_15_x86_64/bin:$PATH
      spin: pip -q config --site set global.extra-index-url http://haskell:4033/frank/staging/+simple/
      spin: flake8 --exit-zero ./src ./tests
      ./src/spin/builtin/virtualenv.py:132:22: T100 fixme found (FIXME)
      spin: radon mi -n B ./src ./tests
      >>> ...


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
