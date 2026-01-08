.. Zuspec Software Backend documentation master file

Zuspec Software Backend
=======================

The Zuspec Software (SW) Backend is a code generator that transforms Zuspec 
hardware component models into executable C/C++ software for simulation, 
testing, and modeling.

It provides a complete path from high-level Zuspec component descriptions 
to compiled, runnable C code with full async/sync process support.

Version: 0.0.1

**Quick Links:**

* :doc:`quickstart` - Get started in 5 minutes
* :doc:`api` - API Reference
* :doc:`examples` - Example transformations
* `GitHub Repository <https://github.com/zuspec/zuspec-be-sw>`_

.. toctree::
   :maxdepth: 2
   :caption: User Guide:

   quickstart
   generator
   features
   examples

.. toctree::
   :maxdepth: 2
   :caption: Reference:

   api
   
.. toctree::
   :maxdepth: 1
   :caption: Development:
   
   testing
   contributing

Key Features
------------

* **Component Translation**: Converts Zuspec Components to C structs and functions
* **Async/Sync Processes**: Transforms async methods to C code with optional sync conversion
* **Protocol Interfaces**: Generates C API structs for Protocol types
* **Type Mapping**: Maps Zuspec types to appropriate C types
* **Memory Management**: Automatic lifecycle management for components
* **Validation**: Pre-generation validation of datamodel compatibility
* **Compilation**: Built-in compiler interface with GCC support
* **Test Execution**: Test runner for automated verification
* **Type Specialization**: Optional monomorphization for performance (experimental)

Getting Started
---------------

Install the package:

.. code-block:: bash

   pip install zuspec-be-sw

Basic usage:

.. code-block:: python

   import zuspec.dataclasses as zdc
   from zuspec.be.sw import CGenerator, CValidator, CCompiler, TestRunner
   from pathlib import Path

   @zdc.dataclass
   class Counter(zdc.Component):
       count: int = zdc.field(default=0)
       
       def increment(self):
           self.count += 1
           
       def get_count(self) -> int:
           return self.count

   # Build datamodel
   factory = zdc.DataModelFactory()
   ctxt = factory.build(Counter)

   # Validate
   validator = CValidator()
   assert validator.validate(ctxt)

   # Generate C code
   gen = CGenerator(Path("output"))
   sources = gen.generate(ctxt)

   # Compile
   compiler = CCompiler(Path("output"))
   exe = compiler.compile(sources, Path("output/test"))

   # Run
   runner = TestRunner()
   result = runner.run(exe)

This generates and runs executable C code from the Zuspec component.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
