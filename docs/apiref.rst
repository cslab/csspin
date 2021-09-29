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
.. autofunction:: interpolate1
.. autofunction:: interpolate
.. autofunction:: namespaces
.. autofunction:: toporun

Communication with the user
===========================

.. autofunction:: echo
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
.. autofunction:: exists
.. autofunction:: mkdir
.. autofunction:: rmtree

.. autofunction:: download

.. autofunction:: readtext
.. autofunction:: readlines
.. autofunction:: writetext
.. autofunction:: writelines
.. autofunction:: appendtext
.. autofunction:: readbytes
.. autofunction:: writebytes
.. autofunction:: persist
.. autofunction:: unpersist
