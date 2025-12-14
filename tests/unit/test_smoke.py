#****************************************************************************
# Copyright 2019-2025 Matthew Ballance and contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#****************************************************************************
import pytest
import zuspec.dataclasses as zdc
from pathlib import Path

from zuspec.be.sw import CGenerator, CValidator, CCompiler, TestRunner


def test_smoke(tmpdir):

    @zdc.dataclass
    class MyC(zdc.Component):

        def hello(self):
            print("Hello")

    # 1. Transform MyC to datamodel representation
    dm_ctxt = zdc.DataModelFactory().build(MyC)
    # The key uses __qualname__ which includes the function name for local classes
    myc_dm = list(dm_ctxt.type_m.values())[0]
    assert myc_dm is not None
    assert myc_dm.name == 'MyC' or myc_dm.name.endswith('.MyC')

    # 2. Validate that dm representation can be mapped to C
    validator = CValidator()
    assert validator.validate(dm_ctxt), f"Validation failed: {validator.errors}"

    # 3. Transform dm representation to C
    generator = CGenerator(output_dir=tmpdir)
    sources = generator.generate(dm_ctxt)
    assert len(sources) > 0

    # 4. Compile runtime code, generated code, and test harness
    compiler = CCompiler(output_dir=tmpdir)
    executable = Path(tmpdir) / "test_myc"
    result = compiler.compile(sources, executable, extra_includes=[Path(tmpdir)])
    assert result.success, f"Compilation failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    # 5. Run and confirm functionality: implementation of 'print' shows Hello
    runner = TestRunner()
    test_result = runner.run(executable, expected_output="Hello")
    assert test_result.passed, f"Test failed:\nstdout: {test_result.stdout}\nstderr: {test_result.stderr}"



