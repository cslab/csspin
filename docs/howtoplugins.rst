.. -*- coding: utf-8 -*-
   Copyright (C) 2024 CONTACT Software GmbH
   All rights reserved.
   https://www.contact-software.com/

==========================
 Plugin Development Guide
==========================

Plugins are Python modules that add tasks and other behaviors to *spin*. Since
spin is only a task runner, leveraging the full power requires importing
plugin-packages containing a set of plugins or adding project-local plugins.

The plugins used by a project must be declared under the ``plugins`` key. As
plugins can *require* other plugins to work, it is generally not necessary to
declare all plugins a project actually uses, as lower-level plugins are imported
automatically. For example, the `spin_python.pytest`_ plugin naturally requires
the `spin_python.python`_ plugin, so it is unnecessary to also include
`spin_python.python`_ (it won't hurt either, though).

.. NOTE::
   Any modification of the ``plugin-packages``, ``plugin-path`` and ``plugins``
   may require to call :option:`--provision <spin --provision>` in order to
   install and provision plugin-packages, plugins and their dependencies.

**Project-local plugins** are modules in plugin directories and can be declared
using their relative path to the project via ``plugin-path``. Local plugins can
then by used adding their name. Given a project layout like this:

  .. code-block:: console
    :caption: Project-local plugin file hierarchy
    :emphasize-lines: 4-6

    $ tree  .
    .
    ├── spinfile.yaml
    ├── spinplugins
    │   ├── myplugin.py
    │   └── myplugin_schema.yaml
    └── ...

  ``myplugin`` can be used like so:

  .. code-block:: yaml
    :caption: ``spinfile.yaml`` defining a project-local plugin

    # 'plugin-path' is a list of relative paths from where plugins are imported.
    plugin-path:
      - spinplugins
    plugins:
      - myplugin

**Plugin-packages** containing a set of plugins are declared in
``plugin-packages``. spin will install installable plugins into
``.spin/plugins``.

  .. code-block:: yaml
    :caption: ``spinfile.yaml`` defining plugins to import from plugin-packages

    # 'plugin-packages' is a list of plugin-packages which are to be installed
    # during provision and provide a set of plugins.
    plugin-packages:
      - spin_python
    plugins:
      - spin_python.python

Plugin lifecycle
================

#. On startup `spin` makes sure that all plugin-packages requested by
   ``spinfile.yaml`` are available by installing installable plugin-packages and
   their plugins that are not yet installed. Project-local plugins simply get
   imported.

#. Then, plugins are topologically sorted by their dependencies and imported in
   that order: if plugin ``B`` requires plugin ``A`` to be present, the import
   order is ``A`` first, then ``B`` etc.

#. All plugins can ship a ``<plugin_name>_schema.yaml`` that defines the
   plugins' schema including the structure, types and help strings. This schema
   is loaded into the :ref:`configuration tree
   <configuration-tree-system-label>` under the name of the plugin. E.g. for a
   plugin called ``myplugin``. The plugin settings would end up in the
   configuration three as:

   .. code-block:: yaml
      :caption: Subtree of a plugin added to spin's configuration tree

      myplugin:
        setting1: ...
        setting2: ...

#. When a plugin has a module-level ``defaults`` variable, the existing plugin
   configuration in the configuration tree is updated by the content defined by
   ``defaults``.

   .. code-block:: python
      :caption: Defining plugin defaults within the plugin module
      :emphasize-lines: 4

      from spin import config


      defaults = config(setting1="...", setting2=config(foo="bar"))

#. `spin` then starts to invoke callbacks provided by the plugins. *All callback
   functions are optional*. Callbacks are invoked in topological dependency
   order. The following callbacks are available:

   A. The ``configure(cfg)`` functions of all plugins are called in topological
      order. ``configure`` is meant to manipulate the configuration tree by
      modifying or adding settings. This is useful for plugins to modify their
      behavior or subtree based on values of other plugins that are already
      loaded.

   #. If `spin` is in cleanup mode via the :option:`--cleanup <spin --cleanup>`
      command line option, each plugins' ``cleanup(cfg)`` function is called.
      ``cleanup`` is meant to remove stuff from the filesystem that has been
      provisioned by the plugin before. Cleanup functions are executed in
      inverse topological order.

   #. If `spin` is in provisioning mode via the :option:`--provision <spin
      --provision>` option, each plugins' ``provision(cfg)`` callback is called.
      This is meant to create stuff in the filesystem, e.g. a
      `spin_python.python`_ plugin may create a Python virtual environment here.

   #. After all provisioning callbacks have been processed, each plugins'
      ``finalize_provision(cfg)`` callback is invoked. This is meant to
      post-process the provisioned resources. E.g. the `spin_python.python`_
      installs all collected Python dependencies into the virtual environment.

   #. Each plugin's ``init(cfg)`` callback is invoked. This is meant to prepare
      the environment for using the resources provisioned by the plugin. For
      example, the `spin_python.python`_ plugin activates the virtual
      environment here.

#. Finally the actual tasks is executed.

.. Note::
  The cleanup and provisioning steps B, C and D, will *only* be called when the
  provisioning options :option:`--cleanup <spin --cleanup>` or
  :option:`--provision <spin --provision>` have been used.

  ``init(cfg)`` on the other hand will only be called in case a subcommand is to
  be executed.


Developing plugins
==================

Plugins are Python modules that are imported by ``spin``, doing whatever
side-effects are required. Plugins are loaded in one of the following ways:

* plugins that are listed under the ``plugins`` key of ``spinfile.yaml`` or
  ``global.yaml``

* plugins that are listed as requirements in another plugin's configuration
  subtree under the ``requires.spin`` key


The plugin API consists of the following:

* An optional module-level variable ``defaults`` holding a configuration subtree
  created by :py:func:`config <spin.config>`. This configuration tree will be
  merged with project, global settings and the plugins schema to become the
  configuration subtree named like the plugin.

* An optional ``configure(cfg)`` callback that is called before ``init``. Here,
  plugins can manipulate the configuration tree so that subsequent callbacks of
  other plugins behave differently. Note that the configuration tree is not yet
  fully resolved, meaning values still contain values to be interpolated like
  ``"{spin.cache}"``, meaning that during the ``configure(cfg)`` callback,
  accessing properties should be done via :py:func:`spin.interpolate1` or by
  passing the values to spins API that will resolve values internally (e.g.
  :py:func:`spin.sh` via ``sh("ls {spin.cache}")``).

* An optional ``init(cfg)`` callback that is called before any subcommand is
  executed, but after ``configure(cfg)``. ``init(cfg)`` can be used to setup
  state after all plugins have been configured.

* An optional ``provision(cfg)`` callback that is called when the
  :option:`--provision <spin --provision>` command line flag is used. E.g. the
  `spin_python.python`_ plugin provisions a Python interpreter in its
  ``provision(cfg)``.

* An optional ``cleanup(cfg)`` callback that is called when running
  :option:`--cleanup <spin --cleanup>`. This is used to unprovision
  dependencies, e.g. the `spin_python.python`_ plugin removes the installation
  tree of the Python interpreter as well as its virtual environment.

Callbacks are called in "dependency" order, i.e. the plugin dependency graph (as
given by ``requires``) is topologically sorted.

Further, importing a plugin can have side-effects like adding subcommands to
``spin`` by using the decorators ``@task`` and ``@group``.

Here is an example for a simple plugin:

  .. code-block:: python
    :linenos:
    :caption: Example: A simple spin plugin module

    # We assume that this plugin module is called "example", providing
    # a subcommand of the same name.

    from spin import config, echo, task

    defaults = config(msg="Spin's cache is located at {spin.cache}")


    @task()
    def example(cfg):
        """Example plugin"""
        echo(cfg.example.msg)

Furthermore, each plugin should provide a ``<plugin_name>_schema.yaml`` that
defines the schema of the subtree it adds to the configuration tree. It
additionally defines how spin should handle the types of properties and their
help strings.

  .. code-block:: yaml
    :caption: <plugin_name>_schema.yaml of an example plugin

    example: # must match the plugin name
      type: object # subtrees are objects
      help: This is an example plugin
      properties:
        msg:
          type: str
          help: |
            The value of this property will be echo'ed when the plugins'
            "example"-task is executed.

To activate this plugin, it has to be declared in ``spinfile.yaml``:

  .. code-block:: yaml
    :caption: ``spinfile.yaml`` demonstrating how to add a local example plugin

    plugins:
      - example   # assuming 'example' is available somewhere in sys.path

By this, ``spin`` gains a new subcommand ``example`` which we can use to print
our message:

  .. code-block:: console
    :caption: Use the new "example" command
    :emphasize-lines: 5,7

    $ spin --help
    ...
    Commands:
    ...
      example    Example plugin
    ...
    $ spin example
    spin: This project lives in .

Plugin schema
=============

All plugins should provide a valid schema as they provide further information
about the plugin and its properties in the configuration tree, enabling path
normalization, type validation and enforcement as well as documenting
properties.

In order to benefit from those features, a plugin must provide a custom schema.

For an external plugin, e.g. ``pytest``, the plugin should ship
``pytest_schema.yaml``. Please note that no default values are set here.

  .. code-block:: yaml
    :caption: Example: Excerpt of a non-builtin plugin schema

    # pytest_schema.yaml
    pytest: # name of the plugin
      type: object
      help: This is the pytest plugin for cs.spin
      properties:
        coverage:
          type: bool
          help: Run the pytest plugin in coverage mode.
        opts:
          type: list
          help: |
              Optional options to pass to the pytest call when running the pytest
              task.

There are some more constraints and notable details:

- All properties must have the following keys: ``type`` and ``help``.

- ``type: object``-configured entries don't have a default value.

- All property values regardless of their type definition in schema can also be
  ``callable``. If they are callable, they must be evaluated while
  ``configure(cfg)`` of the respective plugin is called. E.g. ``defaults =
  config(setting=myfunc)`` requires ``func(cfg)`` to be called within
  ``configure(cfg)`` and return a value to be assigned to ``setting``.

- Default values should be defined in the Python module of the plugin and *not
  within the schema*.

- Values that won't have a valid YAML type (valid types: object/dict, list, str,
  int, float, bool), during runtime can't be represented in the schema. These
  must be defined in the plugins module using ``defaults = spin.config(...).``

- Properties with default values that are initially ``None`` (``defaults =
  config(key=None)``) and will have a valid type during runtime (e.g. set
  during ``configure(cfg)``) must set a default value of ``""`` in
  ``<plugin_name>_schema.yaml`` via ``default: ""``.

- Property-key names should be representable as environment variables, allowing
  letters, digits and single underscores where underscores should not be leading
  or trailing. Constrains are not enforced, since these special cases do occur
  in practice, as plugins define their part of the config tree within the
  ``config()``-call whereas the Python syntax permits assignments like
  ``config(foo.bar="value")`` and ``config(1foo="value")``. Otherwise,
  properties can't be overridden by environment variables.

As mentioned schemas are used to assign types to properties. The available
types are referenced below.

.. list-table:: Available property types
   :widths: 20 80
   :header-rows: 1

   * - Type
     - Description
   * - ``internal``
     -
       * additional type that hides a property from :option:`--dump <spin --dump>`
       * permits the modification of properties via CLI and environment variables
       * can be used like ``type: path internal``
   * - ``object``
     - Python ``dict`` / :py:class:`spin.tree.ConfigTree` for mapping key-value
       pairs
   * - ``path``
     - :py:class:`path.Path` object that provides modern path operations
   * - ``list``
     - literal list, i.e. a list containing only strings
   * - ``str``
     - a typical string
   * - ``float``
     - floating point number
   * - ``int``
     - integer values
   * - ``bool``
     - boolean values

Spin handles types of configuration tree properties as defined in the respective
schemas. Since lists are designed to store multiple elements, they're all
treated as strings for simplicity. The following configuration would result in
``foo.bar`` being a list of strings.

.. code-block:: yaml
   :caption: `spinfile.yaml` limitations of properties marked

   foo:
     bar:
         - {"name": "lili", "age": 54}
         - {"name": "lala", "age": 23}


Plugin API
==========

The API for plugin development is defined in :py:mod:`spin`. The general idea is
to keep plugin scripts short and tidy, similar to shell scripts of commands in a
Makefile. Thus, :py:mod:`spin` provides simple, short-named Python function to
do things like manipulating files and running programs.

Arguments to spin APIs are automatically interpolated against the configuration
tree.

Here is a simple example using the core functions of spins API:

.. code-block:: python
   :linenos:
   :caption: Basic Spin API usage by a dummy plugin

   from spin import cd, die, echo, exists, sh, task, config, mkdir, setenv

   defaults = config(cache="{spin.cache}/dummy")


   def configure(cfg):
       """Configure the plugin and apply changes to the configuration tree"""
       ...


   def provision(cfg):
       """
       Provision the plugin, usually by creating directories and downloading
       additional tools.
       """

       if not exists(cfg.dummy.cache):
           mkdir(cfg.dummy.cache)


   def cleanup(cfg):
       """Remove files that should not maintain on the machine"""

       rmtree(cfg.dummy.cache)


   def init(cfg):
       """The init will be called before a task is executed"""

       # One might set environment variables here as well
       setenv(OUTPUT_FILE_NAME="file.txt")


   @task()
   def dummy(cfg):
       """This is a dummy plugin"""

       echo(f"This project is located in {cfg.spin.project_root}")

       with cd(cfg.spin.project_root):
           # We can pass each argument to a command separately,
           # which saves us from quoting stuff correctly:
           sh("ls", "-l", "spinfile.yaml")

           # Assuming dummy.cache is defined as `type: path` in dummy_schema.yaml
           file_path = cfg.dummy.cache / "{OUTPUT_FILE_NAME}"

           # We can also simply use whole command lines:
           sh(f"echo {cfg.spin.project_root} > {file_path}")

           if not exists(file_path):
               die("I didn't expect that!")

Conventions and guidelines
==========================

To optimize spin's user experience and reduce the mental/memorizing load on the
developers using the spin plugins, we should strive for a consistent user
interface and behavior. To achieve it, we introduce some conventions to be
followed when programming the spin plugins. The following sections cover the
details.

General recommendations
-----------------------

Coding standards
~~~~~~~~~~~~~~~~

The source code should be compliant with our `Python Coding Guide`_.

Idempotence
~~~~~~~~~~~~

Plugins provisioning them selfs by installing packages, downloading and caching
resources, as well as creating and modifying required file system structures,
must ensure, that a second or third provision doesn't break the setup. Ideally a
second provision call of the same plugin won't do anything.

OS-independency
~~~~~~~~~~~~~~~

Plugins should be designed to work with Windows as well as Unix-based operating
systems including not only the provision and run, but also covering topics like
path normalization and logging.

Prefer spin APIs
~~~~~~~~~~~~~~~~

To offer consistent behavior, plugins should prefer using spin API to similar
APIs from the standard libraries and packages. E.g. prefer
:py:func:`spin.rmtree` over :py:func:`shutil.rmtree`.

Short and descriptive naming
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The name of a plugin should be as well descriptive as short. The latter is
important since it is also used as the name of the node of the plugin-specific
config-subtree, so a over-long names makes for unnecessarily long
config-three-paths which are more difficult to handle on CLI etc. In case you're
wrapping a tool, "plugin-name == task-name == tool-name" makes for a good UX in
many cases.

Choose the name of the task such that it is easy to type. It will be used a lot
on command line. Example:

.. code-block:: console

   $ spin pytest
   spin: activate /home/bts/src/qs/spin/cs.spin/.spin/venv
   spin: pytest -m 'not slow' tests
   ...

Fail early
~~~~~~~~~~

When triggering potentially long-running processes depending on some conditions
which may not be fulfilled, it is nice to check the latter early and fail fast.
A typical example is a missing secret, the according check may look as below:

.. code-block:: python
   :caption: Example for early failure due to missing secret

   def configure(cfg):
       if (
           cfg.mkinstance.dbms == "postgres"
           and not cfg.mkinstance.postgres.postgres_syspwd
       ):
           spin.die(
               "Please provide the PostgreSQL system password in the"
               f" property 'mkinstance.postgres.postgres_syspwd'"
           )

Consider the outside-of-CONTACT usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We want to address the automation demand outside CONTACT/SD in the future, too.
So, for many spin plugins, we have to expect the usage outside CONTACT, in a
different organization with different infrastructure. That means that the plugin
should not hardcode assumptions about the location of infrastructure services
and other CONTACT specifics. Even though this is not yet planned, this should be
kept in mind when developing new plugins and plugin-packages.

Configuration tree
------------------

The configuration tree is explained in :ref:`configuration-tree-system-label`,
while there are some conventions to follow:

#. Strive for clean and compact configuration sub-trees. Do not dump everything
   that could be configurable in some corner-case into it.
#. If your plugin drives a tool and the executable name can vary for some
   reasons: use the property "exe"(?) to configure the name of the latter.
#. Plugins wrapping tools should consider providing a list of arguments names
   "args" which is appended/inserted to the command line calling the tool.
#. The default-values of configuration properties shipped with the plugins
   should match the need in the majority of cases.
#. When provisioning third-party packages, you usually want to soft pin the major
   segment of their version.

   **Reasoning**: we depend on the behavior of the tools and especially on their
   CLIs. If left unpinned, (major) tool updates would eventually break the
   plugin. On the other hand, we would like to avoid the tedious "raise the
   pinning to the next version" maintenance efforts. So, the sweet spot here is
   a partial pin which allows the bug fixes and minor changes to "flow" and
   avoids breaking changes. For Python dependencies, the compatibility operator
   is appropriate in many situations:
   ``requires=config(python=["cpplint~=1.6.7"])``

Moreover, we can differentiate between two ways of modeling the
config-tree of a spin plugin:

#. "Mkinstance model" or "the cs.recipes-way"

   - We provide a configuration property for every(\*) CLI parameter of
     mkinstance
   - We compute the values of some of those to ease the usage
   - The plugin itself has some logic to call additional tools in
     certain circumstances

   This is because mkinstance is central to our development model and
   thus heavily used by developers, which want to control different
   CLI params independently.

   Pros:

   - every CLI param can be controlled easily an independently
   - automatically computed values ease the usage of the tool
   - you don't have to set every option in your spinfile,
     defaults "match" in many situations

   Cons:

   - The configuration tree is essentially bound to the CLI of the
     tool with all the negative effects (e.g. plugin breakage by
     minor changes of tools' CLI)

#. The "behave model" or "the Makefile-way"

   The task runner plugin is a thin layer above the tool and doesn't
   provide dedicated control for every CLI option. Instead, we provide
   generic option lists to customize the tool calls, i.e. something like:

   .. code-block:: python

      defaults = config(opts=["--format=pretty", "--no-source"], tests=["tests/accepttests"])


      @task()
      def behave(cfg):
          """Run the 'behave' command."""
          sh("behave", *cfg.opts, *cfg.tests)

   If the tool has a more complex CLI with ordering constraints, we would
   provide such generic lists for every "block" in the CLI.

   Pros:

   - results in simple plugins implementations
   - results in simple configuration trees
     Cons:
   - Customizing the calls is (at least) less comfortable and readable

Most plugins should follow the second model.

Transparency and behavior consistency
-------------------------------------

Spins plugin API is designed is to fully log all relevant commands and changes
to the environment during all phases of the program life cycle. Plugins should
make proper use of it and avoid hiding important commands and actions. The
best-case scenario would be that each command logged by spin and its plugins can
be copied and entered into a fresh environment creating the exact same state as
spin does.

Therefore:

- The command lines used to make subprocess calls have to be printed
  on the standard out stream and highlighted consistently. For the
  most cases just call the spin-API :py:func:`spin.sh` like follows:

  .. code-block:: python

     from spin import sh

     sh(npm, "install", "-g", req)

  If it doesn't work for your case, try to approximate its behavior.

- Setting the environment variables should be echoed in the output,
  too. Just call the spin API as follows:

  .. code-block:: python

     from spin import setenv

     ...
     setenv(
         COVERAGE_PROCESS_CONFIG=cfg.myplugin.config,
         COVERAGE_PROCESS_START=None,
     )

- When the plugin does something meaningful and notable without
  calling a subprocess, print a note to standard output, too:

  .. code-block:: python

     from spin import info

     info(f"Create {coverage_path}")

Moreover, to have the output layed out consistently, the plugins are discouraged
to write to standard output stream directly via :py:func:`print` & Co; instead,
use according spin APIs (:py:func:`spin.echo`, :py:func:`spin.info`,
:py:func:`spin.warning`, :py:func:`spin.error`, :py:func:`spin.die`).


Secret management
-----------------

Often, the plugins have to deal with secrets (typically auth-credentials) or
other more-or-less sensitive information (like names of internal infrastructure
endpoints).

Those secrets obviously can't be part of the plugin implementation, including
the configuration defaults (where they belong semantically in many cases).

Canonical solution for that problem is pulling those secrets from the
configuration tree property and interpolating the default value from an
environment variable, i.e. something like this:

.. code-block:: python
   :caption: Secret usage within a plugin

   from spin import config

   defaults = config(postgres=config(postgres_syspwd="{POSTGRES_SYSPWD}"))

That way we can provide the secrets conveniently as well on CI/CD as
AWS/production as on dev-workstations. Additionally, developers have the
additional benefit to control the according configuration properties via private
unshared ``global.yaml`` (see :ref:`writing-global-label`).

.. TODO:: More of tdocs/plugin_guideline.md?
