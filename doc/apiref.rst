.. -*- coding: utf-8 -*-
   Copyright (C) 2024 CONTACT Software GmbH
   All rights reserved.
   https://www.contact-software.com/

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
