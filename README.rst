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

Motivating Example
==================

.. code-block:: console

   $ spin lint
   spin: cd /Users/frank/Projects/spin
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
   spin: /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1/bin/python -m virtualenv -q -p /Users/frank/.spin/macosx_10_15_x86_64/python/3.8.1/bin/python ./cp38-macosx_10_15_x86_64
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
   spin: ./cp38-macosx_10_15_x86_64/bin/pip -q install -e .
   spin: set PATH=/Users/frank/Projects/spin/cp38-macosx_10_15_x86_64/bin:$PATH
   spin: flake8 ./src ./tests


