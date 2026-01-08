#######
Testing
#######

Testing guide for zuspec-be-sw.

Running Tests
=============

Run all tests:

.. code-block:: bash

   pytest

Run unit tests:

.. code-block:: bash

   pytest tests/unit/

With coverage:

.. code-block:: bash

   pytest --cov=zuspec.be.sw

Writing Tests
=============

Test template:

.. code-block:: python

   def test_feature(tmpdir):
       @zdc.dataclass
       class MyComp(zdc.Component):
           def method(self):
               print("test")

       ctxt = zdc.DataModelFactory().build(MyComp)
       validator = CValidator()
       assert validator.validate(ctxt)

       gen = CGenerator(Path(tmpdir))
       sources = gen.generate(ctxt)
       
       compiler = CCompiler(Path(tmpdir))
       exe = compiler.compile(sources, Path(tmpdir) / "test")
       
       runner = TestRunner()
       result = runner.run(exe)
       assert result.passed
