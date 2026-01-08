############
Contributing
############

Development guide for zuspec-be-sw.

Setup
=====

.. code-block:: bash

   git clone https://github.com/zuspec/zuspec-be-sw
   cd zuspec-be-sw
   pip install -e ".[dev]"
   pytest

Workflow
========

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Run test suite
5. Submit PR

Code Style
==========

* Use Black formatting
* Add docstrings
* Follow PEP 8

PR Requirements
===============

* Pass CI tests
* Include tests
* Update docs
* Clear commits
