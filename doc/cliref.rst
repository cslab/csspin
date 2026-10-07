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

.. _cliref-label:

======================
Command Line Reference
======================

.. click:: csspin.cli:commands
   :prog: spin


.. _shell-completion-label:

Shell Completion
================

Spin supports :kbd:`Tab` completion for Bash, Zsh, Fish, and PowerShell.
To enable it, generate the completion script for your shell with
:option:`--generate-shell-completion <spin --generate-shell-completion>`
and load it when the shell starts.

Bash
----

Add this to ``~/.bashrc``:

.. code-block:: bash

   eval "$(spin --generate-shell-completion bash)"

Zsh
---

Add this to ``~/.zshrc``:

.. code-block:: zsh

   eval "$(spin --generate-shell-completion zsh)"

Fish
----

Save the script output to Fish's completions directory:

.. code-block:: fish

   spin --generate-shell-completion fish > ~/.config/fish/completions/spin.fish

PowerShell
----------

Add this to your PowerShell profile (``$PROFILE``):

.. code-block:: powershell

   spin --generate-shell-completion powershell | Out-String | Invoke-Expression

After modifying your shell configuration, open a new shell for the changes to take effect. :kbd:`Tab` completion should now work.
