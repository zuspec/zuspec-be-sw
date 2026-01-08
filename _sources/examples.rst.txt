########
Examples
########

Complete examples demonstrating Zuspec SW backend usage.

Simple Counter
==============

Basic component with state:

.. code-block:: python

   @zdc.dataclass
   class Counter(zdc.Component):
       count: int = zdc.field(default=0)
       
       def increment(self):
           self.count += 1
       
       def get_value(self) -> int:
           return self.count

Protocol Interface
==================

Component implementing a protocol:

.. code-block:: python

   from typing import Protocol

   class DataIF(Protocol):
       def send(self, data: int) -> int: ...

   @zdc.dataclass  
   class Sender(zdc.Component):
       api: DataIF = zdc.export()
       
       def send(self, data: int) -> int:
           print(f"Sending {data}")
           return data * 2

Async Component
===============

Component with async methods:

.. code-block:: python

   @zdc.dataclass
   class AsyncSender(zdc.Component):
       async def send_data(self, value: int):
           print(f"Start: {value}")
           await self.wait(100)
           print(f"Done: {value}")

Full Workflow
=============

Complete example from definition to execution:

.. code-block:: python

   import zuspec.dataclasses as zdc
   from zuspec.be.sw import *
   from pathlib import Path

   @zdc.dataclass
   class Calculator(zdc.Component):
       result: int = zdc.field(default=0)
       
       def add(self, a: int, b: int) -> int:
           self.result = a + b
           return self.result
       
       def test(self):
           assert self.add(2, 3) == 5
           print("Tests passed!")

   factory = zdc.DataModelFactory()
   ctxt = factory.build(Calculator)
   
   validator = CValidator()
   assert validator.validate(ctxt)

   gen = CGenerator(Path("build"))
   sources = gen.generate(ctxt)

   compiler = CCompiler(Path("build"))
   exe = compiler.compile(sources, Path("build/test"))

   runner = TestRunner()
   result = runner.run(exe)
   assert result.passed
