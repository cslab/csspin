==========================
 Plugin Development Guide
==========================

Plugins are Python modules that add tasks and other behaviours to
`spin`. While `spin` has a number of built-in plugins for common
stacks and tools, it is easy to add project-local plugins or create
Python packages to implement other plugins.

The plugins used by a project must be declared under the ``plugins``
key. As plugins can *require* other plugins to work, it is generally
not necessary to declare *all* plugins a project actually uses, as
lower-level plugins are pulled in automatically. For example, the
`pytest` plugin naturally requires the `python` plugin, so it is
unnecessary to also include `python` (it won't hurt either, though).

**Project-local plugins** are modules in some subdirectory of the
project. Plugin directories can be declared using ``plugin-path``.
Local plugins can then by used adding their name prefixed with a
``.``. Given a project layout like this:

.. code-block:: console

   $ tree  .
   .
   ├── spinfile.yaml
   ├── spinplugins
   │   └── myplugin.py
   └── ...

``myplugin`` can be used like so (note the dot!):

.. code-block:: yaml

   # spinfile.yaml

   # 'plugin-path' is a list of relative paths from where plugins are
   # imported
   plugin-path:
     - spinplugins

   plugins:
     - myplugin

**Installable plugins** are declared in ``plugin-packages``. `spin`
will install installable plugins into ``{spin.plugin_dir}``, which is
``{spin.project_root}/.spin/plugins`` unless the plugin path was
modified by the :option:`--plugin-directory <spin --plugin-directory>`
command line option.


Plugin Lifecycle
================

1. When `spin` starts, it makes sure that all plugins requested by
   ``spinfile.yaml`` are availabe by installing installable plugins that
   are not yet installed.

2. Then, plugins are topologically sorted by their dependencies and
   are imported in that order: if plugin ``B`` requires plugin ``A``
   to be present, the import order is ``A`` first, then ``B`` etc.

3. When a plugin has a module-level ``defaults`` variable, its content
   is added to the configuration tree under the name of the
   plugin. E.g. for a plugin called ``myplugin``:

   .. code-block:: python

      # myplugin
      from spin import config

      defaults = config(setting1="...", setting2="...")

   The plugin settings would end up in the configuration three as:

   .. code-block:: yaml

      myplugin:
        setting1: ...
	setting2: ...

4. `spin` then starts to invoke callbacks provided by the plugins. All
   callback functions are optional. Callbacks are invoked in
   topological dependency order.

5. The ``configure(cfg)`` functions of all plugins are called in
   topological order. ``configure`` is meant to manipulate the
   configuration tree by modifying or adding settings. For example,
   the `python` plugin sets ``PYENV_VERSION`` here when using `pyenv`,
   to select the Python version requested by the project.

6. If `spin` is in cleanup mode via the :option:`--cleanup <spin
   --cleanup>` command line option, each plugins' ``cleanup(cfg)``
   function is called. ``cleanup`` is meant to remove stuff from the
   filesystem that has been provisioned by the plugin before.

7. If `spin` is in provisioning mode via the :option:`--provision
   <spin --provision>` option, each plugins' ``provision(cfg)``
   callback is called. This is meant to create stuff in the
   filesystem, e.g. the `virtualenv` plugin creates a Python virtual
   environment here.

8. After all provisioning callbacks have been processed, each plugins'
   ``finalize_provision(cfg)`` callback is invoked. This is meant to
   post-process the provisioned resources. E.g. the `virtualenv`
   plugin patches the activation scripts here.

9. Each plugin's ``init(cfg)`` callback is invoked. This is meant to
   prepare the environment for using the resources provisioned by the
   plugin. For example, the `virtualenv` plugin activates the virtual
   environment here.

Note,that the cleanup and provisioning steps 6, 7 and 8, will *only*
be called when the provisioning options :option:`--cleanup <spin
--cleanup>` or :option:`--provision <spin --provision>` have been
used.

Using the command line option :option:`--log-level=debug <spin
--log-level>`, `spin` can output a detailed log of callback
invocations.

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
  configuration subtree created by `config()`; this configuration
  tree will be merged with project and global settings and become the
  configuration subtree named like the plugin

* an optional ``configure(cfg)`` callback that is called before
  ``init``; here, plugins can manipulate the configuration tree so
  that subsequent callbacks of other plugins behave differently

* an optional ``init(cfg)`` callback that is called before any
  subcommand is executed, but after ``configure``; ``init`` can be
  used to setup state after all plugins have been configured.

* an optional ``provision(cfg)`` callback that is called by the ``spin
  provision``, or implicitly when the ``--provision`` command line
  option is used. E.g. the **python** plugin provisions a Python
  interpreter in its ``init``.

* an optional ``cleanup(cfg)`` callback that is called when running
  ``spin cleanup``; this is used to unprovision dependencies, e.g. the
  **python** plugin removes the installation tree of the Python
  interpreter it provided it ``init`` callback

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

The API for plugin development is defined in :py:mod:`spin`. The
general idea is to keep plugin scripts short and tidy, similar to
shell scripts of commands in a Makefile. Thus, :py:mod:`spin` provides
simple, short-named Python function to do things like manipulating
files and running programs.

Arguments to spin APIs are automatically interpolated against
the configuration tree.

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
