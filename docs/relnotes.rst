===============
 Release Notes
===============

0.2
===

Core
----

* provisioning is no longer automatic, but has to be explicitly
  requested by using ``--provision``; this avoids the provisioning
  checks for every command invocation, making spin much faster (the
  inverse is ``--cleanup``).

* removed all the magic from importing plugins: ``plugins`` now simply
  has the list of plugin modules, while ``plugin-packages`` lists pip
  requirements and ``plugin-paths`` lists subdirectories of
  ``project_root`` where local plugins are found

* added a simple system for building prerequisites (``build-rules``)

* added a mandatory ``minimum-spin`` key

* replace ``spin exec`` with ``spin run``

* ``spin shell`` activates an environment in a sub-shell

* ``spin system-provision`` supports the provisioning of machine-level
  dependencies to be installed by tools like ``apt``

* spin now uses XDG paths, i.e. :envvar:`XDG_CACHE_HOME` for
  environments and provisioned dependencies, and
  :envvar:`XDG_CONFIG_HOME` for configuration files

* environments are created out-of-tree in :file:`$XDG_CACHE_HOME/spin`
  (which defaults to ``~/.cache/spin``)


Python
------

* ``python.version`` is now mandatory

* development dependencies for Python go into ``python.requirements``

* the Python plugin recognizes an installed ``pyenv`` and re-uses it

pre-commit
----------

* new plugin for ``pre-commit``

Docker
------

* new plugin for Docker (preliminary)


Sphinx
------

* new plugin for Sphinx documentation
