#!/usr/bin/env python3
"""RTL ALU Example with @comb and @sync processes"""
import tempfile
from pathlib import Path
import zuspec.dataclasses as zdc
from zuspec.be.sw import CGenerator

@zdc.dataclass
class SimpleALU(zdc.Component):
    a : zdc.bit16 = zdc.input()
    b : zdc.bit16 = zdc.input()
    result : zdc.bit16 = zdc.output()
    
    @zdc.comb
    def _alu_logic(self):
        self.result = self.a ^ self.b

print("Generating C code for SimpleALU...")
factory = zdc.DataModelFactory()
ctx = factory.build(SimpleALU)

with tempfile.TemporaryDirectory() as tmpdir:
    generator = CGenerator(output_dir=tmpdir)
    sources = generator.generate(ctx)
    
    c_file = Path(tmpdir) / "simplealu.c"
    print("\nGenerated C code:\n")
    print(c_file.read_text())
    print("\n✅ Success!")
