#!/usr/bin/env python3
"""Test C code generation for RTL features (input/output, @comb, @sync)"""

import pytest
import tempfile
import subprocess
from pathlib import Path
import zuspec.dataclasses as zdc
from zuspec.be.sw import CGenerator, CCompiler


def test_simple_comb_codegen(tmpdir):
    """Test C code generation for simple combinational logic"""
    
    @zdc.dataclass
    class SimpleALU(zdc.Component):
        a : zdc.bit16 = zdc.input()
        b : zdc.bit16 = zdc.input()
        result : zdc.bit16 = zdc.output()
        
        @zdc.comb
        def _alu_logic(self):
            self.result = self.a ^ self.b
    
    # Build datamodel
    factory = zdc.DataModelFactory()
    ctx = factory.build(SimpleALU)
    
    # Generate C code
    generator = CGenerator(output_dir=str(tmpdir))
    sources = generator.generate(ctx)
    
    # Check files were generated (lowercase names)
    assert len(sources) > 0
    h_file = Path(tmpdir) / "simplealu.h"
    c_file = Path(tmpdir) / "simplealu.c"
    assert h_file.exists(), f"Header file not found. Files: {list(Path(tmpdir).iterdir())}"
    assert c_file.exists(), f"C file not found. Files: {list(Path(tmpdir).iterdir())}"
    
    # Check header contains input/output fields (Note: bit16 maps to int32_t for now)
    h_content = h_file.read_text()
    assert " a;" in h_content, f"Input 'a' not found in header"  # input
    assert " b;" in h_content, f"Input 'b' not found in header"  # input
    assert " result;" in h_content, f"Output 'result' not found in header"  # output
    
    # Check C file contains comb process function
    c_content = c_file.read_text()
    assert "_alu_logic" in c_content or "alu_logic" in c_content, f"Comb process not found in C file"
    assert "self->result = (self->a ^ self->b)" in c_content, f"Comb logic not found in C file"
    assert "/* Sensitive to: a, b */" in c_content, f"Sensitivity list not found"


def test_sync_codegen(tmpdir):
    """Test C code generation for synchronous processes"""
    
    @zdc.dataclass
    class Counter(zdc.Component):
        clock : zdc.bit = zdc.input()
        reset : zdc.bit = zdc.input()
        count : zdc.bit16 = zdc.output()
        
        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _counter(self):
            if self.reset:
                self.count = 0
            else:
                self.count = self.count + 1
    
    # Build datamodel
    factory = zdc.DataModelFactory()
    ctx = factory.build(Counter)
    
    # Generate C code
    generator = CGenerator(output_dir=str(tmpdir))
    sources = generator.generate(ctx)
    
    # Check files were generated (lowercase names)
    h_file = Path(tmpdir) / "counter.h"
    c_file = Path(tmpdir) / "counter.c"
    assert h_file.exists()
    assert c_file.exists()
    
    # Check for sync process
    c_content = c_file.read_text()
    assert "_counter" in c_content or "counter" in c_content


def test_mixed_sync_comb_codegen(tmpdir):
    """Test C code generation for component with both sync and comb"""
    
    @zdc.dataclass
    class RegisteredALU(zdc.Component):
        clock : zdc.bit = zdc.input()
        reset : zdc.bit = zdc.input()
        a : zdc.bit16 = zdc.input()
        b : zdc.bit16 = zdc.input()
        result : zdc.bit16 = zdc.output()
        _alu_out : zdc.bit16 = zdc.field()
        
        @zdc.comb
        def _alu_logic(self):
            self._alu_out = self.a ^ self.b
        
        @zdc.sync(clock=lambda s: s.clock, reset=lambda s: s.reset)
        def _output_reg(self):
            if self.reset:
                self.result = 0
            else:
                self.result = self._alu_out
    
    # Build datamodel
    factory = zdc.DataModelFactory()
    ctx = factory.build(RegisteredALU)
    
    # Generate C code
    generator = CGenerator(output_dir=str(tmpdir))
    sources = generator.generate(ctx)
    
    # Check files were generated (lowercase names)
    h_file = Path(tmpdir) / "registeredalu.h"
    c_file = Path(tmpdir) / "registeredalu.c"
    assert h_file.exists()
    assert c_file.exists()
    
    c_content = c_file.read_text()
    assert "_alu_logic" in c_content or "alu_logic" in c_content
    assert "_output_reg" in c_content or "output_reg" in c_content


@pytest.mark.skip(reason="Requires runtime support for RTL execution")
def test_comb_execution(tmpdir):
    """Test that generated C code for comb logic compiles and executes"""
    
    @zdc.dataclass
    class XorGate(zdc.Component):
        a : zdc.bit = zdc.input()
        b : zdc.bit = zdc.input()
        y : zdc.bit = zdc.output()
        
        @zdc.comb
        def _xor(self):
            self.y = self.a ^ self.b
    
    # Build datamodel
    factory = zdc.DataModelFactory()
    ctx = factory.build(XorGate)
    
    # Generate C code
    generator = CGenerator(output_dir=str(tmpdir))
    sources = generator.generate(ctx)
    
    # Create test harness
    test_c = Path(tmpdir) / "test_xor.c"
    test_c.write_text("""
#include "XorGate.h"
#include <stdio.h>
#include <assert.h>

int main() {
    XorGate gate;
    XorGate_init(&gate);
    
    // Test XOR truth table
    gate.a = 0; gate.b = 0;
    XorGate__xor(&gate);
    assert(gate.y == 0);
    
    gate.a = 0; gate.b = 1;
    XorGate__xor(&gate);
    assert(gate.y == 1);
    
    gate.a = 1; gate.b = 0;
    XorGate__xor(&gate);
    assert(gate.y == 1);
    
    gate.a = 1; gate.b = 1;
    XorGate__xor(&gate);
    assert(gate.y == 0);
    
    printf("XOR gate test passed\\n");
    return 0;
}
""")
    
    # Compile
    compiler = CCompiler(output_dir=tmpdir)
    executable = Path(tmpdir) / "test_xor"
    assert compiler.compile(sources + [test_c], executable)
    
    # Run
    result = subprocess.run([str(executable)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "passed" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
