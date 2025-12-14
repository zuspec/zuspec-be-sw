# Implementation Plan: C Backend for zuspec-be-sw-simplify

**Date:** 2024-12-14

## Overview

This document outlines the implementation plan for completing the TODO items in `tests/unit/test_smoke.py`. The goal is to transform Python dataclass-based component definitions into C code, compile it, and execute it.

## Current State

### Available Infrastructure

1. **DataModelFactory** (`zuspec.dataclasses.DataModelFactory`)
   - Transforms Python `@zdc.dataclass` decorated classes into a datamodel representation
   - Returns a `Context` object with `type_m` dict containing datamodel types
   - Usage: `dm_ctxt = zdc.DataModelFactory().build(MyC)`

2. **Datamodel Types** (`zuspec.dataclasses.dm`)
   - `DataTypeComponent` - Component with fields, functions, bind_map
   - `DataTypeProtocol` - Interface/Protocol with method definitions
   - `DataTypeStruct` - Pure data types
   - `Function` - Method representation with args, body, return type
   - `Process` - `@process` decorated async methods
   - `Field` - Component fields with `FieldKind` (port, export, field)
   - Expression types: `ExprBin`, `ExprCall`, `ExprAttribute`, `ExprConstant`, etc.
   - Statement types: `StmtAssign`, `StmtFor`, `StmtIf`, `StmtReturn`, etc.

3. **Visitor Pattern** (`zuspec.dataclasses.dm.Visitor`)
   - Dynamic visitor that auto-generates visit methods for datamodel types
   - Used via `@dm.visitor(dm)` decorator

4. **JsonConverter Pattern** (`zuspec.dataclasses.dm.JsonConverter`)
   - Similar to Visitor but for JSON serialization
   - Good reference implementation for building a C code generator

5. **C Runtime Documentation** (`docs/internals.md`)
   - Coroutine-based threading model (`zsp_thread_t`, `zsp_frame_t`)
   - Stack-based memory allocation
   - Scheduler for thread management (`zsp_scheduler_t`)
   - Virtual function table pattern for type polymorphism

6. **Mapping Documentation** (`docs/mapping.md`)
   - `zdc.Component` maps to C struct with `zsp_component_t` base
   - Method parameters/return types have explicit types
   - `print` maps to `fprintf` with format string conversion

### Missing Infrastructure

1. **C Code Generator** - No implementation in `src/zuspec/be/sw/`
2. **C Runtime Library** - Referenced in docs but not present in repo
3. **Compilation Helpers** - No build/test execution framework
4. **C Compatibility Validator** - No validation that datamodel can map to C

---

## Implementation Tasks

### Task 1: Transform MyC to Datamodel Representation

**Status:** Already available via `DataModelFactory`

**Implementation:**
```python
import zuspec.dataclasses as zdc
dm_ctxt = zdc.DataModelFactory().build(MyC)
myc_dm = dm_ctxt.type_m[MyC.__qualname__]
```

**Work Required:** None - just use existing API.

---

### Task 2: Validate that DM Representation Can Be Mapped to C

**Purpose:** Check that all datamodel constructs used are supported by the C backend.

**Work Required:**

1. **Create `src/zuspec/be/sw/validator.py`**
   - Implement a Visitor-based validator
   - Check supported types: int, struct, component, protocol
   - Check supported statements: assign, for, if, return, expr
   - Check supported expressions: bin ops, calls, attributes, constants
   - Report unsupported constructs with clear error messages

2. **Validation Rules:**
   - All types must have C-compatible representations
   - No Python-specific constructs (generators, comprehensions initially)
   - Method signatures must have typed parameters and returns
   - Async methods must follow coroutine pattern

**Example Structure:**
```python
@dm.visitor(dm)
class CValidator(dm.Visitor):
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def visitDataTypeComponent(self, obj):
        # Validate component structure
        for field in obj.fields:
            self.validate_field(field)
        for func in obj.functions:
            self.visit(func)
    
    def visitFunction(self, obj):
        # Validate function can be mapped to C
        if obj.args:
            for arg in obj.args.args:
                if arg.annotation is None:
                    self.errors.append(f"Argument {arg.arg} missing type annotation")
    
    def is_valid(self) -> bool:
        return len(self.errors) == 0
```

---

### Task 3: Transform DM Representation to C

**Purpose:** Generate C source code from the datamodel.

**Work Required:**

1. **Create `src/zuspec/be/sw/c_generator.py`**
   - Main code generator using Visitor pattern
   - Generates header (.h) and implementation (.c) files

2. **Type Mapping:**
   | Datamodel Type | C Type |
   |---------------|--------|
   | `DataTypeInt(bits=32, signed=True)` | `int32_t` |
   | `DataTypeInt(bits=64, signed=False)` | `uint64_t` |
   | `DataTypeString` | `const char*` |
   | `DataTypeComponent` | `struct <name>` with `zsp_component_t` base |
   | `DataTypeProtocol` | Virtual function table struct |
   | `DataTypeStruct` | `struct <name>` |

3. **Component Generation:**
   ```c
   // Header: myc.h
   typedef struct MyC {
       zsp_component_t     base;
       // Fields
       // Function pointers for methods
       void (*hello)(struct MyC *self);
   } MyC;
   
   void MyC_init(MyC *self);
   void MyC_hello(MyC *self);
   ```

4. **Method/Coroutine Generation:**
   - Sync methods: direct C functions
   - Async methods: coroutine functions following `internals.md` pattern
   ```c
   // For async methods
   typedef struct MyC_run_locals {
       int i;
       int val;
   } MyC_run_locals;
   
   zsp_frame_t* MyC_run(zsp_thread_t *thread, int idx, va_list *args);
   ```

5. **Expression Generation:**
   | Expression | C Code |
   |-----------|--------|
   | `ExprBin(op=ADD, lhs, rhs)` | `(lhs + rhs)` |
   | `ExprCall(func, args)` | `func(args)` |
   | `ExprAttribute(obj, attr)` | `obj->attr` or `obj.attr` |
   | `ExprConstant(value=42)` | `42` |

6. **Statement Generation:**
   | Statement | C Code |
   |----------|--------|
   | `StmtAssign(target, value)` | `target = value;` |
   | `StmtFor(target, iter, body)` | `for (...)` loop |
   | `StmtIf(test, body, orelse)` | `if (test) {...}` |
   | `StmtReturn(value)` | `return value;` |

7. **Key Classes to Implement:**
   ```
   src/zuspec/be/sw/
   ├── __init__.py
   ├── validator.py        # Task 2
   ├── c_generator.py      # Main generator
   ├── type_mapper.py      # DM type -> C type mapping
   ├── expr_generator.py   # Expression code generation
   ├── stmt_generator.py   # Statement code generation
   └── output.py           # File output management
   ```

---

### Task 4: Compile Runtime Code, Generated Code, and Test Harness

**Purpose:** Compile the generated C code with the runtime library.

**Work Required:**

1. **Locate/Create C Runtime Library**
   - The runtime (`zsp_*.h`, `zsp_*.c`) must be available
   - Key files needed:
     - `zsp_thread.h/c` - Thread and coroutine support
     - `zsp_scheduler.h/c` - Scheduler
     - `zsp_component.h/c` - Base component type
     - `zsp_alloc.h/c` - Memory allocation

2. **Create `src/zuspec/be/sw/compiler.py`**
   ```python
   class CCompiler:
       def __init__(self, output_dir: Path):
           self.output_dir = output_dir
           self.runtime_dir = self._find_runtime()
       
       def compile(self, sources: List[Path], output: Path) -> bool:
           """Compile C sources to executable."""
           cmd = [
               "gcc", "-o", str(output),
               *[str(s) for s in sources],
               f"-I{self.runtime_dir}/include",
               f"-L{self.runtime_dir}/lib",
               "-lzsp_runtime"
           ]
           return subprocess.run(cmd).returncode == 0
   ```

3. **Test Harness Generation:**
   ```c
   // test_harness.c
   #include "myc.h"
   #include "zsp_scheduler.h"
   
   int main() {
       zsp_scheduler_t sched;
       zsp_scheduler_init(&sched);
       
       MyC comp;
       MyC_init(&comp);
       comp.hello(&comp);
       
       return 0;
   }
   ```

---

### Task 5: Run and Confirm Functionality

**Purpose:** Execute compiled code and verify correct behavior.

**Work Required:**

1. **Create `src/zuspec/be/sw/runner.py`**
   ```python
   class TestRunner:
       def run(self, executable: Path, 
               expected_output: str = None,
               expected_return: int = 0) -> TestResult:
           result = subprocess.run([str(executable)], 
                                   capture_output=True, text=True)
           return TestResult(
               passed=(result.returncode == expected_return),
               stdout=result.stdout,
               stderr=result.stderr
           )
   ```

2. **Integration in test_smoke.py:**
   ```python
   def test_smoke(tmpdir):
       @zdc.dataclass
       class MyC(zdc.Component):
           def hello(self):
               print("Hello")
       
       # 1. Transform to datamodel
       dm_ctxt = zdc.DataModelFactory().build(MyC)
       
       # 2. Validate
       validator = CValidator()
       validator.validate(dm_ctxt)
       assert validator.is_valid(), validator.errors
       
       # 3. Generate C code
       generator = CGenerator(output_dir=tmpdir)
       sources = generator.generate(dm_ctxt)
       
       # 4. Compile
       compiler = CCompiler(output_dir=tmpdir)
       executable = tmpdir / "test_myc"
       assert compiler.compile(sources, executable)
       
       # 5. Run and verify
       runner = TestRunner()
       result = runner.run(executable)
       assert result.passed
       assert "Hello" in result.stdout
   ```

---

## Implementation Order

1. **Phase 1: Core Generator Framework**
   - `type_mapper.py` - Basic type mapping
   - `c_generator.py` - Skeleton with component/struct generation
   - `output.py` - File writing utilities

2. **Phase 2: Expression & Statement Generation**
   - `expr_generator.py` - All expression types
   - `stmt_generator.py` - All statement types
   - Extend `c_generator.py` to use these

3. **Phase 3: Validation**
   - `validator.py` - Validate DM is C-compatible

4. **Phase 4: Compilation & Execution**
   - `compiler.py` - GCC/Clang invocation
   - `runner.py` - Execute and capture output
   - Locate or create minimal C runtime

5. **Phase 5: Integration & Testing**
   - Complete `test_smoke.py`
   - Add more comprehensive tests

---

## Dependencies

- **C Compiler:** GCC or Clang (detected at runtime)
- **C Runtime Library:** Must be built/available
- **Python packages:** Already available via zuspec-dataclasses

## Open Questions

1. **Runtime Location:** Where is the C runtime library? Is it in this repo or a separate one?
2. **Target Platforms:** What C standards/platforms to support (C99, C11)?
3. **Async Support:** Should initial implementation support async/coroutines or start with sync-only?
4. **Memory Model:** How to handle memory allocation for generated structs?

## File Structure After Implementation

```
src/zuspec/be/sw/
├── __init__.py           # Public API exports
├── validator.py          # Datamodel validation
├── c_generator.py        # Main C code generator
├── type_mapper.py        # Type mapping utilities
├── expr_generator.py     # Expression code generation
├── stmt_generator.py     # Statement code generation
├── output.py             # Output file management
├── compiler.py           # C compilation
└── runner.py             # Test execution

src/                      # (if runtime goes here)
├── CMakeLists.txt
└── runtime/
    ├── include/
    │   ├── zsp_thread.h
    │   ├── zsp_scheduler.h
    │   └── zsp_component.h
    └── src/
        ├── zsp_thread.c
        ├── zsp_scheduler.c
        └── zsp_component.c
```
