.. RDM_system_connector documentation master file, created by
   sphinx-quickstart on Thu Nov 14 10:56:26 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

RDM_system_connector documentation
===================================

Project Synchronization Tool
============================

.. image:: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg
   :target: https://creativecommons.org/licenses/by/4.0/
   :alt: License: CC BY 4.0

This tool is designed to synchronize the entries in a four-tool system, which includes:

- A project registration system (eGroupware)
- An electronic lab book (Rspace)
- An image database (OMERO)
- A long-term netstorage system (LINstore)

The tool achieves this by running a daemon that continuously extracts the entries from these four tools and writes them into a database.

.. toctree::
   :maxdepth: 4
   :caption: Contents:

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`