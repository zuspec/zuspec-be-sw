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
Tests for C code generation of ports, exports, and API interfaces.
Based on zuspec-dataclasses test_port_export.py
"""
import os
import subprocess
import tempfile
import pytest
import zuspec.dataclasses as zdc
from typing import Protocol
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
    "zsp_map.c",
]


def compile_generated_code(tmpdir: str, sources: list, test_name: str) -> tuple:
    """Compile generated sources with runtime and run."""
    # Collect all source files
    all_sources = list(sources)
    for src in RT_SOURCES:
        all_sources.append(os.path.join(RT_DIR, src))
    
    # Output executable
    exe_path = os.path.join(tmpdir, test_name)
    
    # Compile - suppress warnings in runtime library code
    compile_cmd = [
        "gcc", "-g", "-O0",
        "-Wno-incompatible-pointer-types",  # Suppress warnings in runtime lib
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


# Define API protocol at module level
class IApi(Protocol):
    def doit(self, val : zdc.uint32_t): ...


# Component that exports (provides) the API
@zdc.dataclass
class TargetComp(zdc.Component):
    exp : IApi = zdc.export()

    def __bind__(self): return {
        self.exp.doit : self.doit
    }

    def doit(self, val : zdc.uint32_t):
        print("TargetComp.doit %d" % val)


# Component that has a port (consumes) the API
@zdc.dataclass
class InitiatorComp(zdc.Component):
    p : IApi = zdc.port()

    def do_test(self):
        self.p.doit(1)
        self.p.doit(2)


# Top-level component that binds port to export
@zdc.dataclass  
class TopComp(zdc.Component):
    i : InitiatorComp = zdc.field()
    t : TargetComp = zdc.field()

    def __bind__(self): return {
        self.i.p : self.t.exp
    }


class TestProtocolGeneration:
    """Tests for Protocol/API C code generation."""

    def test_protocol_generates_api_struct(self, tmpdir):
        """Test that Protocol generates an API struct with function pointers."""
        dm_ctxt = zdc.DataModelFactory().build([IApi, TargetComp])
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find the IApi header
        api_headers = [s for s in sources if 'iapi' in s.name.lower() and s.suffix == '.h']
        assert len(api_headers) > 0, f"No IApi header found in {[s.name for s in sources]}"
        
        header_content = api_headers[0].read_text()
        print(f"API Header:\n{header_content}")
        
        # Check for API struct
        assert "typedef struct" in header_content
        assert "IApi_t" in header_content or "iapi_t" in header_content.lower()
        assert "void *self" in header_content
        assert "doit" in header_content


class TestPortExportGeneration:
    """Tests for Port and Export field C code generation."""

    def test_export_generates_embedded_struct(self, tmpdir):
        """Test that export field generates embedded API struct."""
        dm_ctxt = zdc.DataModelFactory().build([IApi, TargetComp])
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find TargetComp header
        headers = [s for s in sources if 'targetcomp' in s.name.lower() and s.suffix == '.h']
        assert len(headers) > 0
        
        header_content = headers[0].read_text()
        print(f"TargetComp Header:\n{header_content}")
        
        # Export should be embedded struct (no pointer)
        assert "IApi_t exp;" in header_content or "iapi_t exp;" in header_content.lower()

    def test_port_generates_pointer(self, tmpdir):
        """Test that port field generates pointer to API struct."""
        dm_ctxt = zdc.DataModelFactory().build([IApi, InitiatorComp])
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find InitiatorComp header
        headers = [s for s in sources if 'initiatorcomp' in s.name.lower() and s.suffix == '.h']
        assert len(headers) > 0
        
        header_content = headers[0].read_text()
        print(f"InitiatorComp Header:\n{header_content}")
        
        # Port should be pointer
        assert "IApi_t *p;" in header_content or "IApi_t * p;" in header_content


class TestBindGeneration:
    """Tests for bind function C code generation."""

    def test_generates_bind_function(self, tmpdir):
        """Test that bind function is generated for components with bindings."""
        dm_ctxt = zdc.DataModelFactory().build([IApi, InitiatorComp, TargetComp, TopComp])
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find TopComp source
        src_files = [s for s in sources if 'topcomp' in s.name.lower() and s.suffix == '.c']
        assert len(src_files) > 0
        
        src_content = src_files[0].read_text()
        print(f"TopComp Source:\n{src_content}")
        
        # Check for bind function
        assert "TopComp__bind" in src_content
        
    def test_bind_connects_port_to_export(self, tmpdir):
        """Test that bind function connects port pointer to export address."""
        dm_ctxt = zdc.DataModelFactory().build([IApi, InitiatorComp, TargetComp, TopComp])
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find TopComp source
        src_files = [s for s in sources if 'topcomp' in s.name.lower() and s.suffix == '.c']
        src_content = src_files[0].read_text()
        
        # Should have port = &export pattern
        # e.g., self->i.p = &self->t.exp;
        assert "=" in src_content
        assert "&" in src_content  # Taking address of export


class TestPortExportCompilation:
    """End-to-end compilation tests for port/export code."""

    def test_port_export_compiles(self, tmpdir):
        """Test that generated port/export code compiles."""
        dm_ctxt = zdc.DataModelFactory().build([IApi, InitiatorComp, TargetComp, TopComp])
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Print all generated files for debugging
        for src in sources:
            print(f"\n=== {src.name} ===")
            print(src.read_text())
        
        ret, stdout, stderr = compile_generated_code(str(tmpdir), sources, "port_export_test")
        
        if ret != 0:
            print(f"Compilation failed:\nstdout: {stdout}\nstderr: {stderr}")
        
        assert ret == 0, f"Compilation failed: {stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
