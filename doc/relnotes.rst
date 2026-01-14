.. -*- coding: utf-8 -*-
   Copyright (C) 2025 CONTACT Software GmbH
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

.. This document contains the release notes for csspin. Each release is
   documented in a separate section, starting with the most recent release at
   the top.

   The release section must be renamed to the actual release tag with a prefixed
   "v". The date of the release must be in the format `Month Day, Year`/`"%B %d,
   %Y"`.

    At least one of these subsections must be present for each release:

    - Enhancements
    - Bug Fixes
    - Chores

    Each of these subsection must contain a bulleted list of changes made in the
    release. Each bullet must contain a short description of the change and a
    reference to the issue or merge request where the change was made.

    If required, the additional subsections can be added:

    - Breaking Changes
    - Migration Guide

    These additional subsections must contain a concise description of the
    changes required to migrate from the previous version to the new version.
    This may include code examples, configuration changes, or other relevant
    information to assist users in updating their implementations.

    Example:

    v2.0.2
    ======

    December 10, 2025

    Chores
    ------

    - Add release notes to the documentation structure (`#204 <https://code.contact.de/qs/spin/cs.spin/-/issues/204>`_)
    - Update links in the documentation (`#195 <https://code.contact.de/qs/spin/cs.spin/-/issues/195>`_)
    - Remove outdated TODO in the documentation (`#200 <https://code.contact.de/qs/spin/cs.spin/-/issues/200>`_)

=============
Release Notes
=============

v3.0.0
======

January 14, 2026

Breaking Changes
----------------

- Drop Python 3.9 support (`#210
  <https://code.contact.de/qs/spin/cs.spin/-/issues/225>`_)

Bug Fixes
---------

- ``spin --help`` fails if project is not provisioned (`#209
  <https://code.contact.de/qs/spin/cs.spin/-/issues/209>`_)
- Building python on macOS fails with default config (`#2
  <https://github.com/cslab/csspin/issues/2>`_, (`#221
  <https://code.contact.de/qs/spin/cs.spin/-/issues/221>`_))
- Type hint for ``namespaces()`` incorrect (`!169
  <https://code.contact.de/qs/spin/cs.spin/-/merge_requests/169>`_)

Chores
------

- Add repository URL information to Wheel metadata (`#219
  <https://code.contact.de/qs/spin/cs.spin/-/issues/219>`_)
- Update release process documentation and contribution guideline (`#224
  <https://code.contact.de/qs/spin/cs.spin/-/issues/224>`_)

v2.0.2
======

December 12, 2025

Bug Fixes
---------

- Programs started using spin run might misbehave in some cases (`#215
  <https://code.contact.de/qs/spin/cs.spin/-/issues/215>`_)

Chores
------

- Add release notes to the documentation structure (`#204
  <https://code.contact.de/qs/spin/cs.spin/-/issues/204>`_)
- Remove outdated TODO in the documentation (`#200
  <https://code.contact.de/qs/spin/cs.spin/-/issues/200>`_)
- Deprecation of the `system-provision` subcommand (`#197
  <https://code.contact.de/qs/spin/cs.spin/-/issues/197>`_, `#183
  <https://code.contact.de/qs/spin/cs.spin/-/issues/183>`_)
- Update links in the documentation (`#195
  <https://code.contact.de/qs/spin/cs.spin/-/issues/195>`_)
