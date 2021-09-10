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

**Built-in plugins** are simply listed by their name. To use the
`python` plugin in a project, add its name to the ``plugins`` list:

.. code-block:: yaml

   # spinfile.yaml
   plugins:
     - python


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
     - .myplugin


**Installable plugins** are declared in ``plugins`` as a YAML
dictionary, where some pip requirement is the key, followed by a list
of module names to import.


.. todo:: nonsense

   FIXME: this is nonsense. We should have a *separate* key to list
   plugin install instructions.

.. todo:: plugin subtrees

   FIXME: also, there is a bug in cli.py: plugin subtrees must not use
   the basename of the plugin, but the full, dotted name (except for
   builtin plugins).

.. code-block:: yaml

   # spinfile.yaml

   plugins:
     # Installing from a git repo; note the colon ':', without it this
     # would not be recognized as a YAML key. The colon will be
     # stripped from the requirement.
     - git+https://github.com/acme/best-practices#egg=acme-best-practices:
       - acme_best_practices

     # A package name, possibly with a version constraint.
     - spin-jira>=1.0:
       spin_jira.issues

`spin` will install installable plugins into ``{spin.plugin_dir}``,
which is ``{spin.project_root}/.spin/plugins`` unless the plugin path
was modified by the :option:`--plugin-directory` command line option.


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

6. If `spin` is in cleanup mode via the :option:`--cleanup` command
   line option, each plugins' ``cleanup(cfg)`` function is
   called. ``cleanup`` is meant to remove stuff from the filesystem
   that has been provisioned by the plugin before.

7. If `spin` is in provisioning mode via the :option:`--provision`
   option, each plugins' ``provision(cfg)`` callback is called. This
   is meant to create stuff in the filesystem, e.g. the `virtualenv`
   plugin creates a Python virtual environment here.

8. After all provisioning callbacks have been processed, each plugins'
   ``finalize_provision(cfg)`` callback is invoked. This is meant to
   post-process the provisioned resources. E.g. the `virtualenv`
   plugin patches the activation scripts here.

9. Each plugin's ``init(cfg)`` callback is invoked. This is meant to
   prepare the environment for using the resources provisioned by the
   plugin. For example, the `virtualenv` plugin activates the virtual
   environment here.

Note,that the cleanup and provisioning steps 6, 7 and 8, will *only*
be called when the provisioning options :option:`--cleanup` or
:option:`--provision` have been used.

Using the command line option :option:`--log-level=debug`, `spin` will
show a detailed log of callback invocations.
