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
C code generation tests for timebase functionality.

These tests mirror test_timebase.py but generate C code, compile it,
and verify the runtime behavior matches the Python model.
"""
import os
import re
import subprocess
import tempfile
import pytest
import zuspec.dataclasses as zdc
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
    "zsp_struct.c",
]


def compile_and_run(tmpdir: str, main_code: str, gen_sources: list, test_name: str) -> tuple:
    """Compile generated sources with custom main and runtime, then run."""
    main_src = os.path.join(tmpdir, "main.c")
    with open(main_src, "w") as f:
        f.write(main_code)
    
    all_sources = [main_src] + [str(s) for s in gen_sources if s.name != 'main.c']
    for src in RT_SOURCES:
        all_sources.append(os.path.join(RT_DIR, src))
    
    exe_path = os.path.join(tmpdir, test_name)
    
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
    
    run_result = subprocess.run(
        [exe_path],
        capture_output=True,
        text=True,
        cwd=tmpdir,
        timeout=10
    )
    
    return run_result.returncode, run_result.stdout, run_result.stderr


def generate_component(comp_class, tmpdir):
    """Generate C code for a component class and return (sources, comp_type, header_name)."""
    dm_ctxt = zdc.DataModelFactory().build(comp_class)
    generator = CGenerator(output_dir=tmpdir)
    sources = generator.generate(dm_ctxt)
    
    header_files = [s for s in sources if s.suffix == '.h']
    header_name = header_files[0].name
    header_content = header_files[0].read_text()
    
    match = re.search(r'typedef struct \w+ \{[^}]*\} (\w+);', header_content, re.DOTALL)
    comp_type = match.group(1) if match else header_name.replace('.h', '')
    
    return sources, comp_type, header_name


# Define components at module level so inspect.getsource() can find them
@zdc.dataclass
class SmokeTestComp(zdc.Component):
    """Component for test_smoke - prints time before and after wait."""
    async def doit(self):
        print("Time: %s" % self.time())
        await self.wait(zdc.Time.ns(1))
        print("Time: %s" % self.time())


@zdc.dataclass
class WaitTestComp(zdc.Component):
    """Component for test_wait_advances_time - waits 50ns."""
    async def do_wait(self):
        print("TIME_BEFORE:%llu" % self.time())
        await self.wait(zdc.Time.ns(50))
        print("TIME_AFTER:%llu" % self.time())


@zdc.dataclass  
class MultiWaitTestComp(zdc.Component):
    """Component for test_multiple_waits - multiple sequential waits."""
    async def multi_wait(self):
        print("T0:%llu" % self.time())
        await self.wait(zdc.Time.ns(10))
        print("T1:%llu" % self.time())
        await self.wait(zdc.Time.ns(20))
        print("T2:%llu" % self.time())
        await self.wait(zdc.Time.ns(30))
        print("T3:%llu" % self.time())


@zdc.dataclass
class TimeUnitsTestComp(zdc.Component):
    """Component for test_time_units - tests different time units."""
    async def test_units(self):
        print("T0:%llu" % self.time())
        await self.wait(zdc.Time.us(1))  # 1 microsecond = 1000 ns
        print("T1:%llu" % self.time())
        await self.wait(zdc.Time.ns(500))
        print("T2:%llu" % self.time())


@zdc.dataclass
class PrintFormatTestComp(zdc.Component):
    """Component for test_print_with_format - tests print with format strings."""
    async def doit(self):
        print("start")
        await self.wait(zdc.Time.ns(100))
        print("end at time %d" % 100)


class TestTimebaseCodegen:
    """C code generation tests mirroring test_timebase.py functionality."""

    def test_smoke(self, tmpdir):
        """Test basic component with time printing and wait - mirrors test_smoke."""
        main_template = r'''
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

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    {comp_type} comp;
    {comp_type}_init(&ctxt, &comp, "comp", NULL);

    {comp_type}_doit(&comp, &tb);

    /* Run until complete */
    while (zsp_timebase_has_pending(&tb)) {{
        while (tb.ready_head) {{
            zsp_timebase_run(&tb);
        }}
        if (tb.event_count > 0) {{
            zsp_timebase_advance(&tb);
        }}
    }}

    printf("FINAL_TIME:%llu\\n", (unsigned long long)zsp_timebase_current_ticks(&tb));
    zsp_timebase_destroy(&tb);
    return 0;
}}
'''
        
        tmpdir = str(tmpdir)
        sources, comp_type, header_name = generate_component(SmokeTestComp, tmpdir)
        
        main_code = main_template.format(
                header_name=header_name,
                comp_type=comp_type
        )
        
        rc, stdout, stderr = compile_and_run(tmpdir, main_code, sources, "test_smoke")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        
        assert rc == 0, f"Failed with rc={rc}\nstderr: {stderr}"
        
        # Check output shows time progression
        assert "Time:" in stdout
        assert "FINAL_TIME:1" in stdout  # Should be 1ns at end

    def test_wait_advances_time(self, tmpdir):
        """Test that wait() advances simulation time - mirrors test_wait_advances_time."""
        main_template = r'''
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

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    {comp_type} comp;
    {comp_type}_init(&ctxt, &comp, "comp", NULL);

    {comp_type}_do_wait(&comp, &tb);

    while (zsp_timebase_has_pending(&tb)) {{
        while (tb.ready_head) {{
            zsp_timebase_run(&tb);
        }}
        if (tb.event_count > 0) {{
            zsp_timebase_advance(&tb);
        }}
    }}

    printf("FINAL_TIME:%llu\\n", (unsigned long long)zsp_timebase_current_ticks(&tb));
    zsp_timebase_destroy(&tb);
    return 0;
}}
'''
        
        tmpdir = str(tmpdir)
        sources, comp_type, header_name = generate_component(WaitTestComp, tmpdir)
        
        main_code = main_template.format(
                header_name=header_name,
                comp_type=comp_type
        )
        
        rc, stdout, stderr = compile_and_run(tmpdir, main_code, sources, "test_wait")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        
        assert rc == 0, f"Failed with rc={rc}\nstderr: {stderr}"
        
        # Time should advance by 50ns
        assert "FINAL_TIME:50" in stdout

    def test_multiple_waits(self, tmpdir):
        """Test multiple sequential waits - mirrors test_multiple_waits."""
        main_template = r'''
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

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    {comp_type} comp;
    {comp_type}_init(&ctxt, &comp, "comp", NULL);

    {comp_type}_multi_wait(&comp, &tb);

    while (zsp_timebase_has_pending(&tb)) {{
        while (tb.ready_head) {{
            zsp_timebase_run(&tb);
        }}
        if (tb.event_count > 0) {{
            zsp_timebase_advance(&tb);
        }}
    }}

    printf("FINAL_TIME:%llu\\n", (unsigned long long)zsp_timebase_current_ticks(&tb));
    zsp_timebase_destroy(&tb);
    return 0;
}}
'''
        
        tmpdir = str(tmpdir)
        sources, comp_type, header_name = generate_component(MultiWaitTestComp, tmpdir)
        
        main_code = main_template.format(
                header_name=header_name,
                comp_type=comp_type
        )
        
        rc, stdout, stderr = compile_and_run(tmpdir, main_code, sources, "test_multi")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        
        assert rc == 0, f"Failed with rc={rc}\nstderr: {stderr}"
        
        # Times should be: 0, 10, 30, 60 (cumulative)
        assert "FINAL_TIME:60" in stdout

    def test_time_units(self, tmpdir):
        """Test different time units - mirrors test_time_units."""
        main_template = r'''
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

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    {comp_type} comp;
    {comp_type}_init(&ctxt, &comp, "comp", NULL);

    {comp_type}_test_units(&comp, &tb);

    while (zsp_timebase_has_pending(&tb)) {{
        while (tb.ready_head) {{
            zsp_timebase_run(&tb);
        }}
        if (tb.event_count > 0) {{
            zsp_timebase_advance(&tb);
        }}
    }}

    printf("FINAL_TIME:%llu\\n", (unsigned long long)zsp_timebase_current_ticks(&tb));
    zsp_timebase_destroy(&tb);
    return 0;
}}
'''
        
        tmpdir = str(tmpdir)
        sources, comp_type, header_name = generate_component(TimeUnitsTestComp, tmpdir)
        
        main_code = main_template.format(
                header_name=header_name,
                comp_type=comp_type
        )
        
        rc, stdout, stderr = compile_and_run(tmpdir, main_code, sources, "test_units")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        
        assert rc == 0, f"Failed with rc={rc}\nstderr: {stderr}"
        
        # Final time should be 1000 + 500 = 1500ns
        assert "FINAL_TIME:1500" in stdout

    def test_print_with_format(self, tmpdir):
        """Test print with format string pattern."""
        main_template = r'''
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

    zsp_timebase_t tb;
    zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

    {comp_type} comp;
    {comp_type}_init(&ctxt, &comp, "comp", NULL);

    {comp_type}_doit(&comp, &tb);

    while (zsp_timebase_has_pending(&tb)) {{
        while (tb.ready_head) {{
            zsp_timebase_run(&tb);
        }}
        if (tb.event_count > 0) {{
            zsp_timebase_advance(&tb);
        }}
    }}

    zsp_timebase_destroy(&tb);
    return 0;
}}
'''
        
        tmpdir = str(tmpdir)
        sources, comp_type, header_name = generate_component(PrintFormatTestComp, tmpdir)
        
        main_code = main_template.format(
                header_name=header_name,
                comp_type=comp_type
        )
        
        rc, stdout, stderr = compile_and_run(tmpdir, main_code, sources, "test_print")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        
        assert rc == 0, f"Failed with rc={rc}\nstderr: {stderr}"
        
        assert "start" in stdout
        assert "end at time 100" in stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
