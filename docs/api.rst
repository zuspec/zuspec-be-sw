##############
API Reference
##############

Complete API documentation for zuspec-be-sw.

CGenerator
==========

.. class:: CGenerator(output_dir: Path, enable_specialization: bool = False)

   Main C code generator.
   
   .. method:: generate(ctxt: ir.Context, py_classes: List[Type] = None) -> List[Path]
   
      Generate C code for all types.

CValidator
==========

.. class:: CValidator()

   Validates datamodel compatibility.
   
   .. method:: validate(ctxt: ir.Context) -> bool
   
      Validate the context.

CCompiler
=========

.. class:: CCompiler(output_dir: Path)

   Compiles generated C code.
   
   .. method:: compile(sources: List[Path], output: Path) -> CompileResult
   
      Compile sources to executable.

TestRunner
==========

.. class:: TestRunner()

   Executes test programs.
   
   .. method:: run(executable: Path, expected_output: str = None) -> TestResult
   
      Run and validate executable.

For detailed examples, see :doc:`examples`.
