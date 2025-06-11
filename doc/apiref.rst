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

====================
Plugin API Reference
====================

.. automodule:: spin
   :no-members:

Defining tasks
==============

.. autofunction:: task
.. autofunction:: group
.. autofunction:: argument
.. autofunction:: option

Interacting with spin
=====================

.. autofunction:: config
.. autofunction:: invoke
.. autofunction:: get_tree
.. autofunction:: interpolate1
.. autofunction:: interpolate
.. autofunction:: namespaces
.. autofunction:: toporun
.. autodata:: EXPORTS

Communication with the user
===========================

.. autoclass:: Verbosity
.. autofunction:: echo
.. autofunction:: info
.. autofunction:: debug
.. autofunction:: warn
.. autofunction:: error
.. autofunction:: die

Handling Processes
==================

.. autofunction:: sh
.. autofunction:: setenv
.. autoclass:: Command

Handling state
==============

.. autoclass:: Memoizer
.. autofunction:: memoizer

Files and Path handling
=======================

.. autofunction:: cd
.. autofunction:: copy
.. autofunction:: exists
.. autofunction:: mkdir
.. autofunction:: mv
.. autofunction:: rmtree

.. autofunction:: download

.. autofunction:: abspath
.. autofunction:: normpath

.. autofunction:: appendtext
.. autofunction:: getmtime
.. autofunction:: persist
.. autofunction:: readbytes
.. autofunction:: readlines
.. autofunction:: readtext
.. autofunction:: readyaml
.. autofunction:: unpersist
.. autofunction:: writebytes
.. autofunction:: writelines
.. autofunction:: writetext
