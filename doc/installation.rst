.. -*- coding: utf-8 -*-
   Copyright (C) 2024 CONTACT Software GmbH
   https://www.contact-software.com/

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

============
Installation
============

csspin is available at PyPI: https://pypi.org/project/csspin/ and can be
installed using any way you like using :program:`pip`. It is most convenient
to have the ``spin`` command locally installed and always available on your
``PATH``, just like a system command.

One easy way of installing `spin` privately in your home directory is by using
:program:`pipx`, as described in the next section.


Installing with pipx
====================

`pipx`_ is a tool that installs Python packages into a user-specific location
in a user's ``HOME`` directory. You can install it like so:

.. code-block:: console
   :caption: Installation of pipx

   python -m pip install --user pipx
   python -m pipx ensurepath

``ensurepath`` adds ``$HOME/.local/bin`` to your shell's configuration, so
commands from packages installed by ``pipx`` are available in ``PATH``. Make
sure to restart your shell to make the setting effective.

Installing spin is as easy as follows:

.. code-block:: console
   :caption: Installation of csspin using pipx

   pipx install csspin

.. _section-system-requirements:

System requirements
===================

In order to install and run csspin, the following system dependencies are needed:

- Python 3.10 or later
