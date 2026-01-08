########
Features
########

This page describes the key features of the Zuspec Software backend and how they work.

Component Translation
=====================

Basic Components
----------------

Zuspec Components are translated to C structs with associated functions:

.. code-block:: python

   @zdc.dataclass
   class Calculator(zdc.Component):
       result: int = zdc.field(default=0)
       
       def add(self, a: int, b: int) -> int:
           self.result = a + b
           return self.result

Generates:

.. code-block:: c

   typedef struct Calculator {
       int result;
   } Calculator;
   
   void Calculator_init(Calculator *self);
   int Calculator_add(Calculator *self, int a, int b);

Type Mapping
============

Zuspec to C Type Conversion
----------------------------

The backend automatically maps Zuspec types to C types:

=================  ==================
Zuspec Type        C Type
=================  ==================
``zdc.bit``        ``uint8_t``
``zdc.bit8``       ``uint8_t``
``zdc.bit16``      ``uint16_t``
``zdc.bit32``      ``uint32_t``
``zdc.bit64``      ``uint64_t``
``int``            ``int``
``bool``           ``int`` (0/1)
``float``          ``float``
``double``         ``double``
``str``            ``const char*``
=================  ==================

Example:

.. code-block:: python

   @zdc.dataclass
   class TypedComponent(zdc.Component):
       flag: bool = zdc.field(default=False)
       count: int = zdc.field(default=0)
       data: zdc.bit32 = zdc.field(default=0)

Generates:

.. code-block:: c

   typedef struct TypedComponent {
       int flag;
       int count;
       uint32_t data;
   } TypedComponent;

Protocol Interfaces
===================

Protocol Types as APIs
----------------------

Protocol types become C API structs with function pointers:

.. code-block:: python

   from typing import Protocol

   class DataIF(Protocol):
       def send(self, data: int) -> int: ...
       def receive(self) -> int: ...

   @zdc.dataclass
   class Sender(zdc.Component):
       api: DataIF = zdc.export()

Generates:

.. code-block:: c

   // Function pointer table
   typedef struct DataIF_vtbl {
       int (*send)(void *self, int data);
       int (*receive)(void *self);
   } DataIF_vtbl;
   
   // Interface wrapper
   typedef struct DataIF {
       void *impl;
       DataIF_vtbl *vtbl;
   } DataIF;
   
   // Sender component
   typedef struct Sender {
       DataIF api;
   } Sender;

Async/Sync Processing
======================

Async Method Handling
---------------------

Methods decorated with ``async`` are analyzed and converted:

.. code-block:: python

   @zdc.dataclass
   class AsyncComponent(zdc.Component):
       async def send_data(self, value: int):
           print(f"Sending: {value}")
           await self.wait(100)
           print("Done")

The backend provides two strategies:

**1. Sync Conversion (Optimization)**

If the async function doesn't actually await anything, it's converted to regular sync:

.. code-block:: c

   void AsyncComponent_send_data(AsyncComponent *self, int value) {
       printf("Sending: %d\\n", value);
       // wait removed since it's the only await
       printf("Done\\n");
   }

**2. State Machine (Full Async)**

If the function has real async operations, generates a state machine:

.. code-block:: c

   enum AsyncComponent_send_data_states {
       STATE_INIT,
       STATE_AFTER_WAIT,
       STATE_DONE
   };
   
   void AsyncComponent_send_data_step(AsyncComponent *self, int value) {
       switch (self->_send_data_state) {
           case STATE_INIT:
               printf("Sending: %d\\n", value);
               // Schedule wait
               self->_send_data_state = STATE_AFTER_WAIT;
               break;
           case STATE_AFTER_WAIT:
               printf("Done\\n");
               self->_send_data_state = STATE_DONE;
               break;
       }
   }

Async Analysis Report
---------------------

The generator prints an analysis report showing conversion decisions:

.. code-block:: text

   Async Analysis Report:
   ======================
   
   Component: AsyncComponent
     send_data: Converted to sync (simple wait pattern)
     process: Requires state machine (complex async)

Memory Management
=================

Component Lifecycle
-------------------

Each component gets initialization and cleanup:

.. code-block:: c

   // Initialization
   void Component_init(Component *self) {
       self->field1 = 0;
       self->field2 = default_value;
   }
   
   // Optional cleanup
   void Component_cleanup(Component *self) {
       // Free any allocated resources
   }

Stack vs Heap Allocation
-------------------------

Components can be allocated on stack or heap:

.. code-block:: c

   // Stack allocation
   MyComponent comp;
   MyComponent_init(&comp);
   MyComponent_method(&comp);
   
   // Heap allocation
   MyComponent *comp = malloc(sizeof(MyComponent));
   MyComponent_init(comp);
   MyComponent_method(comp);
   free(comp);

Validation
==========

Pre-Generation Checks
---------------------

The ``CValidator`` checks compatibility before generation:

.. code-block:: python

   validator = CValidator()
   if not validator.validate(ctxt):
       for error in validator.errors:
           print(f"Error: {error}")

Validation checks:

* All types can be mapped to C
* Method signatures are C-compatible
* No unsupported Python features
* Protocol interfaces are well-formed

Example validation error:

.. code-block:: text

   ValidationError: Type 'MyGeneric[T]' cannot be mapped to C
   ValidationError: Method 'process' uses unsupported *args parameter

Compilation
===========

Built-in Compiler Interface
----------------------------

The ``CCompiler`` class provides compilation support:

.. code-block:: python

   from zuspec.be.sw import CCompiler
   from pathlib import Path

   compiler = CCompiler(output_dir=Path("build"))
   result = compiler.compile(
       sources=[Path("comp.c"), Path("main.c")],
       output=Path("build/test"),
       extra_includes=[Path("include")],
       extra_libs=["-lm"]  # Link math library
   )

   if result.success:
       print("Compilation successful!")
   else:
       print(f"Errors:\\n{result.stderr}")

Compiler Options:

* ``sources``: List of C source files to compile
* ``output``: Output executable path
* ``extra_includes``: Additional include directories
* ``extra_libs``: Extra libraries to link
* ``optimize``: Optimization level (0-3)

The compiler uses GCC by default and includes the zuspec runtime.

Test Execution
==============

Automated Testing
-----------------

The ``TestRunner`` executes and validates generated code:

.. code-block:: python

   from zuspec.be.sw import TestRunner

   runner = TestRunner()
   result = runner.run(
       executable=Path("build/test"),
       expected_output="Expected output text",
       timeout=10
   )

   if result.passed:
       print("✅ Test passed")
       print(f"Output: {result.stdout}")
   else:
       print("❌ Test failed")
       print(f"Expected: {result.expected}")
       print(f"Got: {result.stdout}")

Test runner features:

* Captures stdout and stderr
* Pattern matching for expected output
* Timeout support
* Return code checking
* Detailed result reporting

Type Specialization
===================

Monomorphization (Experimental)
-------------------------------

Enable specialization to generate type-specific code:

.. code-block:: python

   generator = CGenerator(
       output_dir=Path("output"),
       enable_specialization=True
   )

This creates specialized versions of generic code, potentially improving performance
by eliminating dynamic dispatch.

**Without specialization:**

.. code-block:: c

   void process_data(void *data, int type) {
       switch (type) {
           case TYPE_INT: /* ... */
           case TYPE_FLOAT: /* ... */
       }
   }

**With specialization:**

.. code-block:: c

   void process_data_int(int *data) {
       // Specialized for int
   }
   
   void process_data_float(float *data) {
       // Specialized for float
   }

.. note::
   Type specialization is experimental and may increase code size.

Output Organization
===================

File Structure
--------------

Generated files are organized by component:

.. code-block:: text

   output/
   ├── component1.h        # Component header
   ├── component1.c        # Component implementation
   ├── protocol1.h         # Protocol API header
   ├── main.c              # Test harness
   └── runtime/            # Zuspec runtime files

Header Files
------------

Each component gets a header with:

* Type definitions (structs)
* Function declarations
* Include guards
* Required includes

Implementation Files
--------------------

Implementation files contain:

* Function definitions
* Static helper functions
* Initialization code
* Method implementations

Runtime Integration
===================

Zuspec Runtime
--------------

Generated code links with the zuspec runtime, which provides:

* Async scheduling primitives
* Memory management helpers
* Print/IO functions
* Time simulation support

The runtime is automatically included by the compiler.

Debugging Support
=================

Source Comments
---------------

Generated C includes comments linking back to Python:

.. code-block:: c

   /* From: my_component.py:42 MyComponent.process */
   void MyComponent_process(MyComponent *self) {
       /* ... */
   }

Compile with Debug Symbols
---------------------------

.. code-block:: python

   result = compiler.compile(
       sources,
       output,
       extra_flags=["-g", "-O0"]  # Debug symbols, no optimization
   )

Use GDB for debugging:

.. code-block:: bash

   gdb ./build/test
   (gdb) break MyComponent_process
   (gdb) run

Performance Considerations
==========================

Optimization Levels
-------------------

Control C compiler optimization:

.. code-block:: python

   # Debug build
   result = compiler.compile(sources, output, optimize=0)
   
   # Release build
   result = compiler.compile(sources, output, optimize=3)

Async Performance
-----------------

* Sync-converted async is fastest (no overhead)
* State machine async has small overhead
* Many small awaits can be costly
* Consider batch operations

Memory Usage
------------

* Stack allocation is faster than heap
* Small components fit on stack
* Large or long-lived components need heap
* No automatic garbage collection
