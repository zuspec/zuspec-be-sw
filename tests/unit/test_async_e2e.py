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
End-to-end test that compiles and runs generated async C code.

This test creates a Python component with async methods, generates C code,
compiles it with the runtime, and verifies correct execution.
"""
import os
import subprocess
import tempfile
import pytest

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
    "zsp_struct.c",
]


def compile_and_run(tmpdir: str, main_code: str, gen_sources: list, test_name: str) -> tuple:
    """Compile generated sources with custom main and runtime, then run."""
    # Write main source
    main_src = os.path.join(tmpdir, "main.c")
    with open(main_src, "w") as f:
        f.write(main_code)
    
    # Collect all source files
    all_sources = [main_src] + [str(s) for s in gen_sources if s.name != 'main.c']
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
    ] + all_sources
    
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


# Test code that exercises the generated async method
TEST_MAIN_SIMPLE_ASYNC = r'''
#include <stdio.h>
#include <stdlib.h>
#include "zsp_alloc.h"
#include "zsp_init_ctxt.h"
#include "zsp_timebase.h"
#include "{header_name}"

int main(int argc, char **argv) {{
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_init_ctxt_t ctxt;
    ctxt.alloc = &alloc;

    /* Create timebase */
    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    /* Create component */
    {comp_type} comp;
    {comp_type}_init(&ctxt, &comp, "comp", NULL);

    /* Start the async method */
    {comp_type}_doit(&comp, &tb);

    /* Run simulation until complete */
    zsp_timebase_run_until(&tb, ZSP_TIME_NS(1000));

    printf("FINAL_TIME:%llu\\n", (unsigned long long)zsp_timebase_current_ticks(&tb));

    zsp_timebase_destroy(&tb);
    return 0;
}}
'''


# Define component at module level so inspect.getsource() can find it
import zuspec.dataclasses as zdc
from zuspec.be.sw import CGenerator


@zdc.dataclass
class E2EAsyncTestComp(zdc.Component):
    async def doit(self):
        print("before")
        await self.wait(zdc.Time.ns(100))
        print("after")


class TestAsyncE2E:
    """End-to-end tests for async method code generation."""

    def test_async_print_wait_print(self, tmpdir):
        """Test async method with print, wait, print pattern."""
        import re
        
        tmpdir = str(tmpdir)
        dm_ctxt = zdc.DataModelFactory().build(E2EAsyncTestComp)
        generator = CGenerator(output_dir=tmpdir)
        sources = generator.generate(dm_ctxt)
        
        # Find the header file name
        header_files = [s for s in sources if s.suffix == '.h']
        assert len(header_files) > 0
        header_name = header_files[0].name
        
        # Get component type name
        comp_type = header_name.replace('.h', '').upper()
        if comp_type.startswith('_'):
            comp_type = comp_type[1:]
        # Use the actual type name from the generated code
        header_content = header_files[0].read_text()
        # Extract typedef struct name
        match = re.search(r'typedef struct \w+ \{[^}]*\} (\w+);', header_content, re.DOTALL)
        if match:
            comp_type = match.group(1)
        
        print(f"Header: {header_name}")
        print(f"Component type: {comp_type}")
        print(f"Header content:\n{header_content}")
        
        # Print source content for debugging
        for src in sources:
            if src.suffix == '.c' and src.name != 'main.c':
                print(f"\nSource {src.name}:\n{src.read_text()}")
        
        main_code = TEST_MAIN_SIMPLE_ASYNC.format(
            header_name=header_name,
            comp_type=comp_type
        )
        
        rc, stdout, stderr = compile_and_run(tmpdir, main_code, sources, "test_async")
        print(f"rc: {rc}")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        
        # Check compilation succeeded
        assert rc == 0, f"Compilation/run failed with rc={rc}\nstderr: {stderr}"
        
        # Check output contains expected prints
        assert "before" in stdout
        assert "after" in stdout
        assert "FINAL_TIME:" in stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
