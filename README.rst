======
 spin
======

Spin is a task runner that aims so solve the problem of standardizing
workflows for many similar projects. It does this by encapsulating
task definitions in Python packages and automating the provisioning of
development sandboxes and dependencies.

`Documentation <http://frank.pages.contact.de/spin/index.html>`_

Status
======

The up-to-date version is 0.2+, which currently lives in 'master' and
is continuously evolving. It is therefore recommended to do an
editable install using ``pipx`` or ``pip install --user`` from the
cloned repo, and pull regularly:

.. code-block:: console

   $ git clone git@code.contact.de:frank/spin.git
   $ cd spin
   $ pipx install -e .

If installation fails, ``pipx uninstall`` first, and eventually remove
``spin.egg-info`` from ``src`` -- the package had been renamed to
``cs.spin`` in 0.2, and pipx cannot handle this.


The last 0.1 version was 0.1.7, which should not be used any longer.
