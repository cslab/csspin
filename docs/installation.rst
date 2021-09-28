============
Installation
============

Spin requires Python 3.8 or later, and you can install it using any
way you like using :program:`pip`. It is most convenient to have the
``spin`` command locally installed and always available on your
``PATH``, just like a system command.

One easy way of installing `spin` privately in your home directory is
by using :program:`pipx`, as described in the next section.


Installing with Pipx
====================

``pipx`` is a tool that installs Python packages into a user-specific
location in a user's ``HOME`` directory. You can install it like so:

.. code-block:: console

   $ python -m pip install --user pipx
   $ python -m pipx ensurepath

``ensurepath`` adds ``$HOME/.local/bin`` to your shell's
configuration, so commands from packages installed by ``pipx`` are
available in ``PATH``. Make sure to restart your shell to make the
setting effective.

Use ``pipx`` to install spin:

.. code-block:: console

   $ pipx install -i https://packages.contact.de/tools/misc/ cs.spin

The ``spin`` command is now available in your ``PATH``, linked to your
clone of the spin repository. Updating the repository will
automatically give you the most up-to-date version of spin.

Installing from Git
===================

If you want be on the bleeding edge, you can install spin from its
cloned repository:

.. code-block:: console

   $ git clone git@git.contact.de:frank/spin.git
   $ cd spin
   $ pipx install --editable .
