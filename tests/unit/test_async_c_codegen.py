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
"""
End-to-end tests for async method C code generation.
Tests that Python async methods are correctly compiled to C coroutines.
"""
import os
import subprocess
import tempfile
import pytest
import zuspec.dataclasses as zdc
from pathlib import Path

from zuspec.be.sw import CGenerator

# Path to the share directory containing runtime sources and headers
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHARE_DIR = os.path.join(REPO_ROOT, "src", "zuspec", "be", "sw", "share")
RT_DIR = os.path.join(SHARE_DIR, "rt")
INCLUDE_DIR = os.path.join(SHARE_DIR, "include")

# Runtime source files needed for compilation
RT_SOURCES = [
    "zsp_alloc.c",
    "zsp_timebase.c",
    "zsp_list.c",
    "zsp_object.c",
    "zsp_component.c",
]


def compile_generated_code(tmpdir: str, sources: list, test_name: str) -> tuple:
    """Compile generated sources with runtime and run."""
    # Collect all source files
    all_sources = list(sources)
    for src in RT_SOURCES:
        all_sources.append(os.path.join(RT_DIR, src))
    
    # Output executable
    exe_path = os.path.join(tmpdir, test_name)
    
    # Compile
    compile_cmd = [
        "gcc", "-g", "-O0",
        f"-I{INCLUDE_DIR}",
        f"-I{tmpdir}",
        "-o", exe_path
    ] + [str(s) for s in all_sources]
    
    compile_result = subprocess.run(
        compile_cmd,
        capture_output=True,
        text=True,
        cwd=tmpdir
    )
    
    if compile_result.returncode != 0:
        return compile_result.returncode, compile_result.stdout, compile_result.stderr
    
    # Run
    run_result = subprocess.run(
        [exe_path],
        capture_output=True,
        text=True,
        cwd=tmpdir,
        timeout=10
    )
    
    return run_result.returncode, run_result.stdout, run_result.stderr


# Define components at module level so inspect.getsource() can find them
@zdc.dataclass
class AsyncCoroutineTestComp(zdc.Component):
    async def doit(self):
        await self.wait(zdc.Time.ns(1))


@zdc.dataclass
class AsyncPrintWaitTestComp(zdc.Component):
    async def doit(self):
        print("before")
        await self.wait(zdc.Time.ns(100))
        print("after")


@zdc.dataclass
class AsyncHeaderTestComp(zdc.Component):
    async def doit(self):
        await self.wait(zdc.Time.ns(1))


@zdc.dataclass
class AsyncSignatureTestComp(zdc.Component):
    async def run_test(self):
        await self.wait(zdc.Time.ns(1))


@zdc.dataclass
class AsyncPrintFormatTestComp(zdc.Component):
    async def doit(self):
        x = 42
        print("value: %d" % x)
        await self.wait(zdc.Time.ns(1))


class TestAsyncCodeGeneration:
    """Test async method C code generation."""

    def test_async_method_generates_coroutine(self, tmpdir):
        """Test that async method generates coroutine code."""
        dm_ctxt = zdc.DataModelFactory().build(AsyncCoroutineTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Check that files were created
        assert len(sources) > 0
        
        # Find the generated source file
        src_files = [s for s in sources if s.suffix == '.c' and s.name != 'main.c']
        assert len(src_files) > 0
        
        src_content = src_files[0].read_text()
        print(f"Generated source:\n{src_content}")
        
        # Check for coroutine structure
        assert "_task" in src_content
        assert "switch (idx)" in src_content
        assert "zsp_timebase_wait" in src_content

    def test_async_with_print_and_wait(self, tmpdir):
        """Test async method with print and wait."""
        dm_ctxt = zdc.DataModelFactory().build(AsyncPrintWaitTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        src_files = [s for s in sources if s.suffix == '.c' and s.name != 'main.c']
        src_content = src_files[0].read_text()
        print(f"Generated source:\n{src_content}")
        
        # Check for print statements and wait
        assert "fprintf" in src_content
        assert "before" in src_content
        assert "after" in src_content
        assert "ZSP_TIME_NS(100)" in src_content

    def test_header_includes_timebase(self, tmpdir):
        """Test that header includes zsp_timebase.h for async methods."""
        dm_ctxt = zdc.DataModelFactory().build(AsyncHeaderTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find header file
        header_files = [s for s in sources if s.suffix == '.h']
        assert len(header_files) > 0
        
        header_content = header_files[0].read_text()
        print(f"Generated header:\n{header_content}")
        
        assert '#include "zsp_timebase.h"' in header_content

    def test_async_method_signature(self, tmpdir):
        """Test that async method has correct signature with timebase."""
        dm_ctxt = zdc.DataModelFactory().build(AsyncSignatureTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find header file
        header_files = [s for s in sources if s.suffix == '.h']
        header_content = header_files[0].read_text()
        
        # Check function declaration
        assert "zsp_timebase_t *tb" in header_content


class TestAsyncPrintFormatting:
    """Test print() with format strings in async methods."""

    def test_print_format_in_async(self, tmpdir):
        """Test print with % format in async method."""
        dm_ctxt = zdc.DataModelFactory().build(AsyncPrintFormatTestComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        src_files = [s for s in sources if s.suffix == '.c' and s.name != 'main.c']
        src_content = src_files[0].read_text()
        print(f"Generated source:\n{src_content}")
        
        # Should have fprintf with format
        assert "fprintf" in src_content
        assert "value: %d" in src_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
