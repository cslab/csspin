================
Schema Reference
================

.. py:data:: minimum-spin
   :type: 'str internal'

The minimal version of spin, that can process this spinfile. This
property is required.

.. py:data:: spin
   :type: 'object'
   :noindex:

Settings required for running spin. Many of these cannot be set
via a spinfile or via the command line, but are computed by spin.

.. py:data:: spin.spinfile
   :type: 'path'
   :value: 'spinfile.yaml'

The name of the configuration file for the project. This can
be overriden via 'spin -f <filename>'.

.. py:data:: spin.env_base
   :type: 'path internal'
   :value: '{SPIN_CACHE}/{spin.project_hash}'

Where environments are provisioned.

.. py:data:: spin.project_root
   :type: 'path internal'
   :value: '.spin'

The absolute path to the project directory.

.. py:data:: spin.spin_dir
   :type: 'path internal'
   :value: '.spin'

The relative path from <project_root> to spin's project
related data.

.. py:data:: spin.spin_global
   :type: 'path internal'
   :value: '{SPIN_CONFIG}/global.yaml'

User settings that will apply to all projects are read from
this file.

.. py:data:: spin.spin_global_plugins
   :type: 'path internal'
   :value: '{SPIN_CACHE}/plugins'


.. py:data:: spin.plugin_dir
   :type: 'path internal'
   :value: '{spin.env_base}/plugins'


.. py:data:: spin.cruise_spin
   :type: 'path'
   :value: 'spin'


.. py:data:: python
   :type: 'object'


.. py:data:: extra-tasks
   :type: 'object'

`extra-tasks` maps task names to task definitions, where task
definitions support ``env`` and ``script`` keys.

.. py:data:: quiet
   :type: 'boolean'

Spin normally echos the verbatim commands it runs. When `quiet` is
set, this output is suppressed. Additionally, some plugins use
`quiet` to suppress more output of the tools they run.

.. py:data:: verbose
   :type: 'boolean'

When `verbose` is on, spin outputs additional information, like
the time spent running tasks. Some plugins use `verbose` to make
tools more chatty.

.. py:data:: hooks
   :type: 'object'

A dictionary mapping workflow names to lists of commands. This is
automatically set up by the `when` argument to
:py:func:`spin.task`.

.. py:data:: cruise
   :type: 'object'


.. py:data:: plugins
   :type: 'list'

The list of plugins to import.

.. py:data:: plugin-packages
   :type: 'list'

A list of plugin packages to install. Supports the same
requirements specifiers as pip, including URLs, local file names
and PEP 440 specifiers.

.. py:data:: platform
   :type: 'object'


.. py:data:: platform.exe
   :type: 'path'


.. py:data:: platform.shell
   :type: 'path'


.. py:data:: virtualenv
   :type: 'object'


.. py:data:: virtualenv.venv
   :type: 'path'
