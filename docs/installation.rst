============
Installation
============

* Spin requires Python 3.8 or later
* You can install using :program:`pip` in any you way like
* It's most convenient to have the ``spin`` command locally installed
  and always available on your ``PATH``, just like a system command

One way of installing `spin` privately by using :program:`pipx` is
described in the next section.


Installing with Git and Pipx
============================

We currently recommend to install spin directly from its cloned
repository using `pipx
<https://pipxproject.github.io/pipx/>`_.

``pipx`` is a tool that installs Python packages into a user-specific
location in a user's ``HOME`` directory.

Install ``pipx``:

.. code-block:: console

   $ python38 -m pip install --user pipx
   $ python38 -m pipx ensurepath

``ensurepath`` adds ``$HOME/.local/bin`` to your shell's
configuration, so commands from packages installed by ``pipx`` are
available in ``PATH``. Make sure to restart your shell to make the
setting effective.

Use ``pipx`` to install spin:

.. code-block:: console

   $ git clone git@git.contact.de:frank/spin.git
   $ cd spin
   $ pipx install --editable .

The ``spin`` command is now available in your ``PATH``, linked to your
clone of the spin repository. Updating the repository will
automatically give you the most up-to-date version of spin.
