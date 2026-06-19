# Zuspec Software Backend

The Zuspec Software (SW) Backend transforms Zuspec hardware component models into executable C/C++ code for simulation, testing, and modeling.

## Features

- **Component Translation**: Zuspec Components → C structs and functions
- **Async/Sync**: Transforms async methods with optional sync conversion
- **Protocol Interfaces**: Generates C API structs for Protocol types
- **Type Mapping**: Maps Zuspec types to C types
- **Validation**: Pre-generation compatibility checks
- **Compilation**: Built-in GCC compiler interface
- **Test Execution**: Automated test runner
- **Type Specialization**: Optional monomorphization (experimental)
- **PSS → C** *(scenario path)*: compile PSS actions/activities/constraints to a
  self-contained C program via the shared Scenario Runtime IR — runtime
  constraint solving (dv-solve), sequential/`repeat` activities, and
  `parallel`/timed concurrency on the `zsp_timebase` scheduler. See
  [`docs/pss-to-c.md`](docs/pss-to-c.md) and `examples/pss/`. Independent of the
  datamodel-driven `CGenerator` below:

  ```python
  from zuspec.be.sw.scenario import generate_c_files, build_executable
  srcs = generate_c_files(["examples/pss/02_constrained_regs.pss"], "out/", root="pss_top")
  build_executable(srcs, "out/case", "out/")   # → ./out/case <seed> <iters>
  ```

## Installation

```bash
pip install zuspec-be-sw
```

## Quick Start

```python
import zuspec.dataclasses as zdc
from zuspec.be.sw import CGenerator, CValidator, CCompiler, TestRunner
from pathlib import Path

@zdc.dataclass
class Counter(zdc.Component):
    count: int = zdc.field(default=0)
    
    def increment(self):
        self.count += 1
    
    def get_count(self) -> int:
        return self.count

# Build → Validate → Generate → Compile → Run
factory = zdc.DataModelFactory()
ctxt = factory.build(Counter)

validator = CValidator()
assert validator.validate(ctxt)

gen = CGenerator(Path("output"))
sources = gen.generate(ctxt)

compiler = CCompiler(Path("output"))
exe = compiler.compile(sources, Path("output/test"))

runner = TestRunner()
result = runner.run(exe)
```

## Generated C Code

```c
typedef struct Counter {
    int count;
} Counter;

void Counter_init(Counter *self);
void Counter_increment(Counter *self);
int Counter_get_count(Counter *self);
```

## Documentation

- [Quickstart](docs/quickstart.rst)
- [Features](docs/features.rst)
- [Generator](docs/generator.rst)
- [Examples](docs/examples.rst)
- [API](docs/api.rst)
- [Testing](docs/testing.rst)
- [Contributing](docs/contributing.rst)

## Requirements

- Python >= 3.7
- zuspec-dataclasses
- C compiler (GCC)

## License

Apache-2.0
