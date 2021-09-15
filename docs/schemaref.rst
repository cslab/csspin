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
   :value: '{spin.userprofile}/{spin.project_hash}'

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
   :value: '{spin.userprofile}/global.yaml'

User settings that will apply to all projects are read from
this file.

.. py:data:: spin.spin_global_plugins
   :type: 'path internal'
   :value: '{spin.userprofile}/plugins'


.. py:data:: spin.plugin_dir
   :type: 'path internal'
   :value: '{spin.spin_dir}/plugins'


.. py:data:: spin.plugin_packages
   :type: 'list'


.. py:data:: spin.cruise_spin
   :type: 'path'
   :value: 'spin'


.. py:data:: spin.userprofile
   :type: 'path internal'


.. py:data:: python
   :type: 'object'


.. py:data:: extra-tasks
   :type: 'object'


.. py:data:: quiet
   :type: 'boolean'


.. py:data:: verbose
   :type: 'boolean'


.. py:data:: hooks
   :type: 'object'


.. py:data:: cruise
   :type: 'object'


.. py:data:: plugins
   :type: 'list'


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
