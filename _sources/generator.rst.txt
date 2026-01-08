##################
Generator Details
##################

The :class:`~zuspec.be.sw.CGenerator` class is the core component that transforms 
Zuspec IR (Intermediate Representation) into C source code.

Overview
========

The generator performs these key transformations:

1. **Component → C Struct**: Zuspec Components become C structs with functions
2. **Fields → Struct Members**: Component fields become struct members
3. **Methods → C Functions**: Component methods become C functions
4. **Protocols → API Structs**: Protocol types become function pointer structs
5. **Async → State Machines**: Async methods become C state machines or sync code
6. **Types → C Types**: Zuspec types mapped to appropriate C types

Constructor
===========

.. code-block:: python

   CGenerator(output_dir: Path, enable_specialization: bool = False)

Parameters:

* ``output_dir``: Directory where generated C files will be written
* ``enable_specialization``: Enable type specialization/monomorphization (experimental)

Example:

.. code-block:: python

   from pathlib import Path
   from zuspec.be.sw import CGenerator

   generator = CGenerator(
       output_dir=Path("c_gen"),
       enable_specialization=False
   )

Main API
========

generate()
----------

.. code-block:: python

   def generate(self, ctxt: ir.Context, py_classes: List[Type] = None) -> List[Path]:
       """Generate C code for all types in context.
       
       Args:
           ctxt: The datamodel context containing components/protocols
           py_classes: Optional list of Python classes for source introspection
           
       Returns:
           List of paths to generated C source files
       """

This is the main entry point. It:

1. Analyzes async functions for sync conversion
2. Generates protocol/API types
3. Generates component implementations
4. Generates test harness (main.c)
5. Returns list of generated file paths

Example:

.. code-block:: python

   import zuspec.dataclasses as zdc
   from zuspec.be.sw import CGenerator
   from pathlib import Path

   @zdc.dataclass
   class MyComponent(zdc.Component):
       def hello(self):
           print("Hello")

   factory = zdc.DataModelFactory()
   ctxt = factory.build(MyComponent)
   
   generator = CGenerator(Path("output"))
   files = generator.generate(ctxt, py_classes=[MyComponent])
   
   for f in files:
       print(f"Generated: {f}")

Internal Architecture
=====================

Type Mapper
-----------

The ``TypeMapper`` converts Zuspec types to C types:

* ``zdc.bit`` → ``uint8_t``
* ``zdc.bit8`` → ``uint8_t``
* ``zdc.bit16`` → ``uint16_t``
* ``zdc.bit32`` → ``uint32_t``
* ``zdc.bit64`` → ``uint64_t``
* ``int`` → ``int``
* ``bool`` → ``int`` (0/1)
* ``str`` → ``const char*``

Statement Generator
-------------------

The ``StmtGenerator`` converts IR statements to C:

* ``StmtAssign`` → C assignment (``x = y;``)
* ``StmtIf`` → C if/else
* ``StmtWhile`` → C while loop
* ``StmtFor`` → C for loop
* ``StmtReturn`` → C return
* ``StmtExpr`` → C expression statement

Async Analyzer
--------------

The ``AsyncAnalyzer`` examines async functions to determine:

* Which can be converted to sync (no actual async operations)
* Which need full async state machine
* Dependencies between async functions

Report example:

.. code-block:: text

   Async Analysis Report:
   ======================
   
   Component: MyComponent
     send_data: Can convert to sync (no await)
     process: Requires async (uses await)

Async Method Generator
----------------------

The ``DmAsyncMethodGenerator`` creates state machines for async methods:

* State enumeration for each await point
* State variable in component struct
* Switch statement dispatching to states
* Continuation points after awaits

Sync Method Generator
---------------------

The ``SyncMethodGenerator`` handles synchronous methods:

* Direct C function generation
* Local variable declarations
* Expression and statement conversion
* Return value handling

Output Manager
--------------

The ``OutputManager`` organizes generated code:

* Separates headers (.h) and implementation (.c)
* Manages file writing
* Handles includes and dependencies
* Generates main.c harness

Generation Patterns
===================

Component Structure
-------------------

Generated components follow this pattern:

**Header (component.h):**

.. code-block:: c

   #ifndef COMPONENT_H
   #define COMPONENT_H
   
   #include <stdint.h>
   
   typedef struct Component {
       int field1;
       uint32_t field2;
       int _async_state;  // For async methods
   } Component;
   
   void Component_init(Component *self);
   void Component_method1(Component *self);
   int Component_method2(Component *self, int arg);
   
   #endif

**Implementation (component.c):**

.. code-block:: c

   #include "component.h"
   #include <stdio.h>
   
   void Component_init(Component *self) {
       self->field1 = 0;
       self->field2 = 0;
       self->_async_state = 0;
   }
   
   void Component_method1(Component *self) {
       printf("Method1 called\\n");
   }
   
   int Component_method2(Component *self, int arg) {
       return self->field1 + arg;
   }

Protocol Structure
------------------

Protocols become function pointer structs:

.. code-block:: c

   typedef struct DataIF_vtbl {
       int (*send)(void *self, int data);
       void (*receive)(void *self, int *data);
   } DataIF_vtbl;
   
   typedef struct DataIF {
       void *impl;  // Pointer to implementation
       DataIF_vtbl *vtbl;  // Function pointers
   } DataIF;

Async State Machine
--------------------

Async methods become state machines:

.. code-block:: c

   // States for async method
   enum {
       STATE_INIT = 0,
       STATE_AFTER_WAIT1,
       STATE_AFTER_WAIT2,
       STATE_DONE
   };
   
   void Component_async_method_step(Component *self) {
       switch (self->_async_state) {
           case STATE_INIT:
               // Initial code
               self->_async_state = STATE_AFTER_WAIT1;
               break;
           
           case STATE_AFTER_WAIT1:
               // After first await
               self->_async_state = STATE_AFTER_WAIT2;
               break;
           
           case STATE_AFTER_WAIT2:
               // After second await
               self->_async_state = STATE_DONE;
               break;
           
           case STATE_DONE:
               break;
       }
   }

Name Sanitization
-----------------

Python names are converted to valid C identifiers:

* Qualified names: ``module.ClassName`` → ``ClassName``
* Invalid chars: ``my-var`` → ``my_var``
* Leading digits: ``1var`` → ``_1var``
* Reserved words: Prefixed with underscore

Helper function:

.. code-block:: python

   def sanitize_c_name(name: str) -> str:
       if '.' in name:
           name = name.split('.')[-1]
       name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
       if name and name[0].isdigit():
           name = '_' + name
       return name

Type Specialization
===================

When ``enable_specialization=True``, the generator can create specialized versions
of generic code for specific types (monomorphization).

This is experimental and may improve performance by eliminating dynamic dispatch.

Example:

.. code-block:: python

   generator = CGenerator(
       output_dir=Path("output"),
       enable_specialization=True
   )

Best Practices
==============

1. **Provide Python Classes**
   
   Pass original classes for better source introspection:
   
   .. code-block:: python
   
      files = generator.generate(ctxt, py_classes=[MyComp, OtherComp])

2. **Check Generated Code**
   
   Always review generated C for correctness:
   
   .. code-block:: bash
   
      cat c_output/*.c

3. **Use Validation**
   
   Validate before generation to catch issues early:
   
   .. code-block:: python
   
      validator = CValidator()
      assert validator.validate(ctxt)

4. **Handle Async Carefully**
   
   Understand async-to-sync conversion behavior from analysis report.

5. **Organize Output**
   
   Use separate output directories for different builds:
   
   .. code-block:: python
   
      gen_debug = CGenerator(Path("output/debug"))
      gen_release = CGenerator(Path("output/release"))

Limitations
===========

Current Limitations
-------------------

1. **Generic Types**: Limited support for Python generics
2. **Exceptions**: Python exceptions not fully supported in C
3. **Dynamic Features**: Dynamic dispatch limited to protocols
4. **Memory Model**: Simple stack/heap, no advanced GC
5. **Concurrency**: No multi-threading support (single-threaded async)

Future Enhancements
-------------------

* Multi-threading support
* Advanced memory management
* Better generic type support
* Inline optimization hints
* Debug symbol generation
