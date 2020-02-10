Installing
==========

Basic information:

* requires Python 3.8
* currently under development
* should be available on ``PATH``

Recommendation: install from git clone using `pipx
<https://pipxproject.github.io/pipx/>`_ like so:

.. code-block:: console

   $ python38 -m pip install --user pipx
   $ python38 -m pipx ensurepath
   # ... make sure you have pipx in your PATH ...
   $ git clone git@git.contact.de:frank/spin.git
   $ cd spin
   $ pipx install --spec . --editable spin

The ``spin`` command is now available in your PATH.


Overview
========

``spin`` runs programs.

``spin`` expects a `YAML <https://yaml.org/>`_ file named
``spinfile.yaml`` in the top-level folder of the project that declares
tasks, dependencies etc.

``spin`` by itself does nothing. All tasks are defined in *plugin
packages* that have to be activated in ``spinfile.yaml`` using the
``plugins`` key, for example::

  plugins:
    - flake8
    - pytest

``spin`` comes with a set of built-in plugins:

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
   

Where file go
=============

* ``$HOME/.spin/`` -- Python releases and configuration files that are
  not project-specific

* ``<project root>/.spin`` -- plugin packages and project-specific
  settings

* ``<project root>/<venv>`` -- platform/ABI specific virtual
  environment (provisioned by the built-in plugin *virtualenv*)


Plugin API
==========

The API for plugin development is defined in ``spin.api`` (sorry, not
really documented yet).
