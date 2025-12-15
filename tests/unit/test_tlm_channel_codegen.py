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
Tests for TLM Channel C code generation.
Based on zuspec-dataclasses test_tlm.py::test_tlm_channel
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
    "zsp_channel.c",
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
    
    # Compile
    compile_cmd = [
        "gcc", "-g", "-O0",
        "-Wno-incompatible-pointer-types",
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


# Component definitions for TLM Channel tests

@zdc.dataclass
class Producer(zdc.Component):
    """Producer component with a PutIF port."""
    p : zdc.PutIF[int] = zdc.port()

    async def _send(self):
        for i in range(16):
            await self.p.put(i)
            await self.wait(zdc.Time.ns(10))


@zdc.dataclass
class Consumer(zdc.Component):
    """Consumer component with a GetIF port."""
    c : zdc.GetIF[int] = zdc.port()

    @zdc.process
    async def _recv(self):
        while True:
            i = await self.c.get()
            print("Received %d" % i)


@zdc.dataclass
class TopChannel(zdc.Component):
    """Top-level component with producer, consumer, and channel."""
    p : Producer = zdc.field()
    c : Consumer = zdc.field()
    ch : zdc.Channel[int] = zdc.field()

    def __bind__(self): return {
        self.p.p : self.ch.put,
        self.c.c : self.ch.get
    }


class TestChannelDataModelGeneration:
    """Tests for verifying datamodel generation of channel types."""

    def test_channel_datamodel_types(self):
        """Test that Channel, PutIF, GetIF are correctly in datamodel."""
        from zuspec.dataclasses import dm
        
        dm_ctxt = zdc.DataModelFactory().build(TopChannel)
        
        # Verify TopChannel is in context
        assert "TopChannel" in dm_ctxt.type_m
        top_dm = dm_ctxt.type_m["TopChannel"]
        
        # Find the ch field
        ch_field = None
        for f in top_dm.fields:
            if f.name == "ch":
                ch_field = f
                break
        
        assert ch_field is not None, "ch field should exist"
        assert isinstance(ch_field.datatype, dm.DataTypeChannel), \
            f"ch should be DataTypeChannel, got {type(ch_field.datatype).__name__}"
        
        # Verify Producer
        assert "Producer" in dm_ctxt.type_m
        prod_dm = dm_ctxt.type_m["Producer"]
        
        p_field = None
        for f in prod_dm.fields:
            if f.name == "p":
                p_field = f
                break
        
        assert p_field is not None, "p field should exist in Producer"
        assert isinstance(p_field.datatype, dm.DataTypePutIF), \
            f"p should be DataTypePutIF, got {type(p_field.datatype).__name__}"
        
        # Verify Consumer
        assert "Consumer" in dm_ctxt.type_m
        cons_dm = dm_ctxt.type_m["Consumer"]
        
        c_field = None
        for f in cons_dm.fields:
            if f.name == "c":
                c_field = f
                break
        
        assert c_field is not None, "c field should exist in Consumer"
        assert isinstance(c_field.datatype, dm.DataTypeGetIF), \
            f"c should be DataTypeGetIF, got {type(c_field.datatype).__name__}"


class TestChannelCodeGeneration:
    """Tests for C code generation of channel types."""

    def test_channel_header_has_channel_type(self, tmpdir):
        """Test that component with channel has correct header."""
        dm_ctxt = zdc.DataModelFactory().build(TopChannel)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find TopChannel header
        headers = [s for s in sources if 'topchannel' in s.name.lower() and s.suffix == '.h']
        assert len(headers) > 0, f"No TopChannel header found in {[s.name for s in sources]}"
        
        header_content = headers[0].read_text()
        print(f"TopChannel Header:\n{header_content}")
        
        # Should include channel header
        assert '#include "zsp_channel.h"' in header_content
        
        # Should have channel field
        assert "zsp_channel_t ch;" in header_content

    def test_putif_generates_pointer(self, tmpdir):
        """Test that PutIF port generates pointer type."""
        dm_ctxt = zdc.DataModelFactory().build(Producer)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        headers = [s for s in sources if 'producer' in s.name.lower() and s.suffix == '.h']
        assert len(headers) > 0
        
        header_content = headers[0].read_text()
        print(f"Producer Header:\n{header_content}")
        
        # Port should be pointer to interface
        assert "zsp_put_if_t *" in header_content or "zsp_put_if_t * p" in header_content

    def test_getif_generates_pointer(self, tmpdir):
        """Test that GetIF port generates pointer type."""
        dm_ctxt = zdc.DataModelFactory().build(Consumer)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        headers = [s for s in sources if 'consumer' in s.name.lower() and s.suffix == '.h']
        assert len(headers) > 0
        
        header_content = headers[0].read_text()
        print(f"Consumer Header:\n{header_content}")
        
        # Port should be pointer to interface
        assert "zsp_get_if_t *" in header_content or "zsp_get_if_t * c" in header_content

    def test_channel_init_generated(self, tmpdir):
        """Test that channel initialization code is generated."""
        dm_ctxt = zdc.DataModelFactory().build(TopChannel)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find TopChannel source
        src_files = [s for s in sources if 'topchannel' in s.name.lower() and s.suffix == '.c']
        assert len(src_files) > 0
        
        src_content = src_files[0].read_text()
        print(f"TopChannel Source:\n{src_content}")
        
        # Should have channel init call
        assert "zsp_channel_init" in src_content

    def test_channel_bind_generated(self, tmpdir):
        """Test that channel binding code is generated."""
        dm_ctxt = zdc.DataModelFactory().build(TopChannel)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Find TopChannel source
        src_files = [s for s in sources if 'topchannel' in s.name.lower() and s.suffix == '.c']
        src_content = src_files[0].read_text()
        
        print(f"TopChannel Source:\n{src_content}")
        
        # Should have bind function
        assert "TopChannel__bind" in src_content
        
        # Should bind ports to channel interfaces
        assert "zsp_put_if_t" in src_content or "zsp_get_if_t" in src_content


class TestChannelCompilation:
    """End-to-end compilation tests for channel code."""

    def test_channel_code_compiles(self, tmpdir):
        """Test that generated channel code compiles."""
        dm_ctxt = zdc.DataModelFactory().build(TopChannel)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        # Print all generated files for debugging
        for src in sources:
            print(f"\n=== {src.name} ===")
            print(src.read_text())
        
        ret, stdout, stderr = compile_generated_code(str(tmpdir), sources, "channel_test")
        
        if ret != 0:
            print(f"Compilation failed:\nstdout: {stdout}\nstderr: {stderr}")
        
        assert ret == 0, f"Compilation failed: {stderr}"


# Simple channel test component for basic compilation
@zdc.dataclass
class SimpleChannelComp(zdc.Component):
    """Simple component with just a channel for basic tests."""
    ch : zdc.Channel[int] = zdc.field()


class TestSimpleChannelCompilation:
    """Tests for simple channel compilation."""

    def test_simple_channel_compiles(self, tmpdir):
        """Test that a simple channel component compiles."""
        dm_ctxt = zdc.DataModelFactory().build(SimpleChannelComp)
        generator = CGenerator(output_dir=str(tmpdir))
        sources = generator.generate(dm_ctxt)
        
        for src in sources:
            print(f"\n=== {src.name} ===")
            print(src.read_text())
        
        ret, stdout, stderr = compile_generated_code(str(tmpdir), sources, "simple_channel_test")
        
        if ret != 0:
            print(f"Compilation failed:\nstdout: {stdout}\nstderr: {stderr}")
        
        assert ret == 0, f"Compilation failed: {stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
