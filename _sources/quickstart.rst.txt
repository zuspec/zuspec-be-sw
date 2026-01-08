##########
Quickstart
##########

This guide will get you up and running with the Zuspec Software backend in 5 minutes.

Installation
============

Install from PyPI:

.. code-block:: bash

   pip install zuspec-be-sw zuspec-dataclasses

Or for development:

.. code-block:: bash

   git clone https://github.com/zuspec/zuspec-be-sw
   cd zuspec-be-sw
   pip install -e ".[dev]"

You'll also need a C compiler (GCC recommended):

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get install gcc
   
   # macOS
   xcode-select --install

Basic Example
=============

Let's create a simple counter and generate C code:

.. code-block:: python

   import zuspec.dataclasses as zdc
   from zuspec.be.sw import CGenerator, CValidator, CCompiler, TestRunner
   from pathlib import Path

   @zdc.dataclass
   class Counter(zdc.Component):
       """Simple counter component."""
       count: int = zdc.field(default=0)
       
       def increment(self):
           """Increment the counter."""
           self.count += 1
           
       def get_count(self) -> int:
           """Get current count value."""
           return self.count
       
       def run(self):
           """Test the counter."""
           for i in range(5):
               self.increment()
           print(f"Final count: {self.get_count()}")

   # 1. Build datamodel representation
   factory = zdc.DataModelFactory()
   ctxt = factory.build(Counter)

   # 2. Validate compatibility with C backend
   validator = CValidator()
   if not validator.validate(ctxt):
       print(f"Validation errors: {validator.errors}")
       exit(1)

   # 3. Generate C code
   output_dir = Path("c_output")
   generator = CGenerator(output_dir)
   sources = generator.generate(ctxt)
   
   print(f"Generated {len(sources)} C files")

   # 4. Compile the generated code
   compiler = CCompiler(output_dir)
   executable = output_dir / "test_counter"
   result = compiler.compile(sources, executable, extra_includes=[output_dir])
   
   if not result.success:
       print(f"Compilation failed:\\n{result.stderr}")
       exit(1)

   # 5. Run the executable
   runner = TestRunner()
   test_result = runner.run(executable, expected_output="Final count: 5")
   
   if test_result.passed:
       print("✅ Test passed!")
   else:
       print(f"❌ Test failed:\\n{test_result.stdout}")

Generated C Code
----------------

The above generates C code similar to:

**counter.h:**

.. code-block:: c

   typedef struct Counter {
       int count;
   } Counter;
   
   void Counter_init(Counter *self);
   void Counter_increment(Counter *self);
   int Counter_get_count(Counter *self);
   void Counter_run(Counter *self);

**counter.c:**

.. code-block:: c

   #include "counter.h"
   #include <stdio.h>
   
   void Counter_init(Counter *self) {
       self->count = 0;
   }
   
   void Counter_increment(Counter *self) {
       self->count += 1;
   }
   
   int Counter_get_count(Counter *self) {
       return self->count;
   }
   
   void Counter_run(Counter *self) {
       for (int i = 0; i < 5; i++) {
           Counter_increment(self);
       }
       printf("Final count: %d\\n", Counter_get_count(self));
   }

**main.c:**

.. code-block:: c

   #include "counter.h"
   
   int main() {
       Counter counter;
       Counter_init(&counter);
       Counter_run(&counter);
       return 0;
   }

Key Workflow Steps
==================

1. Build Datamodel
------------------

Transform Python Zuspec code to IR:

.. code-block:: python

   factory = zdc.DataModelFactory()
   ctxt = factory.build(MyComponent)

The datamodel captures the structure, types, and behavior in a language-independent representation.

2. Validate
-----------

Check if the component can be mapped to C:

.. code-block:: python

   validator = CValidator()
   if not validator.validate(ctxt):
       for error in validator.errors:
           print(f"Error: {error}")

Validation catches:

* Unsupported type conversions
* Invalid method signatures
* Missing implementations

3. Generate
-----------

Transform datamodel to C source code:

.. code-block:: python

   generator = CGenerator(output_dir)
   sources = generator.generate(ctxt, py_classes=[MyComponent])

Options:

* ``output_dir``: Where to write generated files
* ``enable_specialization``: Enable type specialization (experimental)
* ``py_classes``: Original Python classes for source introspection

4. Compile
----------

Compile C code to executable:

.. code-block:: python

   compiler = CCompiler(output_dir)
   result = compiler.compile(sources, executable_path)

The compiler:

* Uses GCC by default
* Links with zuspec runtime
* Supports custom include paths
* Returns detailed error messages

5. Run & Test
-------------

Execute and verify output:

.. code-block:: python

   runner = TestRunner()
   result = runner.run(executable, expected_output="Expected text")

Test runner features:

* Captures stdout/stderr
* Checks expected output patterns
* Provides detailed results
* Supports timeout

Async Example
=============

Components with async methods are supported:

.. code-block:: python

   from typing import Protocol

   class DataIF(Protocol):
       async def send(self, data: int) -> int: ...

   @zdc.dataclass
   class Sender(zdc.Component):
       async def send_data(self, value: int):
           """Send data asynchronously."""
           print(f"Sending: {value}")
           await self.wait(10)  # Simulate delay
           return value * 2

The backend can:

* Generate async C code with state machines
* Convert to sync code where possible (optimization)
* Handle await expressions and coroutines

Next Steps
==========

* Learn about :doc:`features` - async/sync, protocols, specialization
* Browse :doc:`examples` - complete component examples  
* Read the :doc:`api` - full API reference
* Explore :doc:`generator` - code generation internals
