
# C Runtime
The C runtime library and code that uses it is optimized for efficiency, 
and portability and not necessarily best maintainable software structure.
The code is intended to have fast execution and minimal recurring memory
allocation. It is intended to have very few dependencies, to allow it to
run on deeply embedded targets.


## Code Generation Style
- Use convenience macros for greater readability

## Datatype Structure
Runtime classes are implemented using manually-maintained virtual function
tables. Each type has an initialization function that associates the 
proper table with the instance.

## Threads and Coroutines
The runtime supports a co-routine threading scheme to implement async 
methods. Coroutines execute in the context of a *thread* (see zsp_thread_t). 
Threads maintain a series of storage blocks to hold local variables, track
the call stack of coroutines, and the runnable state of the thread.

### Key Types

- **zsp_scheduler_t**: Manages a queue of runnable threads. Holds a memory
  allocator and runs threads in round-robin fashion via `zsp_scheduler_run()`.
  
- **zsp_thread_t**: Represents an execution context. Contains:
  - `leaf`: Pointer to the current (innermost) stack frame
  - `block`: Linked list of stack storage blocks for frames/locals
  - `flags`: State flags (INITIAL, SUSPEND, BLOCKED)
  - `rval`: Return value from the most recent coroutine return
  - `alloc`: Thread-local allocator (uses stack storage)

- **zsp_frame_t**: A coroutine stack frame containing:
  - `func`: The coroutine function pointer
  - `prev`: Link to the caller's frame  
  - `idx`: Index of the next code block to execute on resume

- **zsp_task_func**: Coroutine function signature:
  `zsp_frame_t *(*)(zsp_thread_t *thread, int idx, va_list *args)`

### Thread Flags

- `ZSP_THREAD_FLAGS_INITIAL`: Set during first call to entry coroutine
- `ZSP_THREAD_FLAGS_SUSPEND`: Thread yielded and should be rescheduled
- `ZSP_THREAD_FLAGS_BLOCKED`: Thread is waiting on an external event

### Stack Memory Management

Threads use a linked list of `zsp_stack_block_t` for storage. Each block
provides a contiguous region that grows upward (`base` toward `limit`).
New blocks are allocated when the current block is exhausted.

- `zsp_thread_alloc_frame()`: Allocates a frame + locals on thread stack
- `zsp_thread_alloca()`: Allocates arbitrary data on thread stack
- `zsp_thread_return()`: Pops frames and frees unused stack blocks

### Coroutine Lifecycle

Co-routines are functions that store their local state in thread-stack
storage. Behavior of a coroutine is broken into one or more synchronous
blocks. The code-block to execute is passed in as the 'idx' parameter.

**First call (idx==0)**
- Function allocates a stack frame via `zsp_thread_alloc_frame()` which
  includes space for local variables
- Parameters are extracted from the 'args' va_list (only valid on idx==0)
- The frame is pushed onto the thread's call stack

**Every call**
- The stack frame and locals are obtained from `thread->leaf`
- A switch statement dispatches to the appropriate code block based on `idx`
- To suspend: set `frame->idx` to the resume block, optionally call
  `zsp_thread_yield()` to mark for rescheduling, then return the frame
- To call another coroutine: use `zsp_thread_call()` which pushes a new frame.
  If the coroutine that zsp_thread_call invokes blocks, zsp_thread_call returns
  the stack frame. If it does not, the return is null. The canonical call looks
  like this:
```
  ret = zsp_thread_call(...);
  if (ret) {
    break;
  }
  // Else, did not block
```

**Final call**
- Calls `zsp_thread_return(thread, rval)` to set the return value
- This pops the frame, frees stack memory, and resumes the caller
- Returns the frame returned by `zsp_thread_return`

### Scheduler Operation

`zsp_scheduler_run()` pops a thread from the queue and executes it:
1. Calls `thread->leaf->func(thread, thread->leaf->idx, NULL)`
2. If thread returns with `SUSPEND` flag, it is rescheduled
3. If thread returns with `BLOCKED` flag, it waits for external wake-up
4. If `thread->leaf` becomes NULL, the thread has completed

### Synchronization Primitives

- **zsp_mutex_t**: Simple mutex with owner tracking and waiter queue
- **zsp_cond_t**: Condition variable with waiter queue

### Helper Macros

- `zsp_frame_size(locals_t)`: Compute frame size for given locals struct
- `zsp_frame_locals(frame, locals_t)`: Cast frame to access locals
- `zsp_task_head_begin/end`: Boilerplate for coroutine function start
- `zsp_task_yield`: Yield and break from current block

---

# Python Code Generator Architecture

The Python code generator (`zuspec.be.sw`) transforms Python dataclass-based 
component definitions into C code that integrates with the C runtime above.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Python Source                                  │
│   @zdc.dataclass                                                        │
│   class MyC(zdc.Component):                                             │
│       def hello(self):                                                  │
│           print("Hello")                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DataModelFactory.build()                           │
│   (from zuspec.dataclasses)                                             │
│   Transforms Python classes into datamodel representation               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          CValidator                                      │
│   Validates datamodel can be mapped to C                                │
│   - Checks supported types, statements, expressions                     │
│   - Reports unsupported constructs                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          CGenerator                                      │
│   Main orchestrator for C code generation                               │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                    │
│   │ TypeMapper  │  │ExprGenerator│  │StmtGenerator│                    │
│   │             │  │             │  │             │                    │
│   │ DM types    │  │ Python AST  │  │ Python AST  │                    │
│   │ → C types   │  │ → C exprs   │  │ → C stmts   │                    │
│   └─────────────┘  └─────────────┘  └─────────────┘                    │
│                                                                         │
│   Output: .h and .c files via OutputManager                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          CCompiler                                       │
│   Compiles generated C with runtime sources                             │
│   - Locates share/rt/*.c and share/include/*.h                         │
│   - Invokes gcc/clang                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          TestRunner                                      │
│   Executes compiled binary and validates output                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### TypeMapper (`type_mapper.py`)

Maps zuspec datamodel types to C type strings:

| Datamodel Type | C Type |
|---------------|--------|
| `DataTypeInt(bits=8, signed=True)` | `int8_t` |
| `DataTypeInt(bits=32, signed=False)` | `uint32_t` |
| `DataTypeString` | `const char*` |
| `DataTypeComponent` | `struct <name>*` |
| `None` | `void` |

Also provides default initializer values for each type.

### ExprGenerator (`expr_generator.py`)

Converts Python AST expressions to C code strings:

| Python Expression | C Code |
|------------------|--------|
| `"Hello"` | `"Hello"` |
| `42` | `42` |
| `True` / `False` | `1` / `0` |
| `a + b` | `(a + b)` |
| `a == b` | `(a == b)` |
| `self.value` | `self->value` |
| `arr[i]` | `arr[i]` |
| `print("Hello")` | `fprintf(stdout, "Hello\n")` |

### StmtGenerator (`stmt_generator.py`)

Converts Python AST statements to C code:

| Python Statement | C Code |
|-----------------|--------|
| `x = 42` | `x = 42;` |
| `x += 1` | `x += 1;` |
| `if x: ...` | `if (x) { ... }` |
| `for i in range(n): ...` | `for (int i = 0; i < n; i += 1) { ... }` |
| `while x: ...` | `while (x) { ... }` |
| `return 42` | `return 42;` |

### CValidator (`validator.py`)

Validates that Python constructs can be mapped to C:

- **Supported expressions**: Call, Constant, Name, BinOp, Compare, 
  Attribute, UnaryOp, Subscript
- **Supported statements**: Expr, Assign, AugAssign, If, For, While, 
  Return, Pass, Break, Continue
- Reports errors for unsupported constructs

### CGenerator (`c_generator.py`)

Main code generator that orchestrates the transformation:

1. **Component Header Generation** (`.h` file):
   - Include guards
   - Struct definition with `zsp_component_t` base
   - Field declarations
   - Function prototypes

2. **Component Implementation** (`.c` file):
   - Init function calling `zsp_component_init()`
   - Method implementations with bodies from Python AST

3. **Test Harness** (`main.c`):
   - Allocator and context setup
   - Component instantiation
   - Method invocation

Key helper: `sanitize_c_name()` converts Python qualified names 
(e.g., `test_func.<locals>.MyC`) to valid C identifiers (`MyC`).

### OutputManager (`output.py`)

Manages generated output files:
- Tracks header and source files
- Creates parent directories
- Writes files atomically

### CCompiler (`compiler.py`)

Compiles generated C code:
- Locates runtime sources in `share/rt/`
- Locates headers in `share/include/`
- Invokes gcc/clang with appropriate flags
- Returns compilation result with stdout/stderr

### TestRunner (`runner.py`)

Executes compiled binaries:
- Runs executable with timeout
- Captures stdout/stderr
- Validates expected output and return code

## File Structure

```
src/zuspec/be/sw/
├── __init__.py           # Public API exports
├── c_generator.py        # Main C code generator
├── compiler.py           # C compilation wrapper
├── expr_generator.py     # Expression code generation
├── output.py             # Output file management
├── runner.py             # Test execution
├── stmt_generator.py     # Statement code generation
├── type_mapper.py        # Type mapping utilities
├── validator.py          # Datamodel validation
└── share/
    ├── include/          # Runtime headers
    │   ├── zsp_alloc.h
    │   ├── zsp_component.h
    │   ├── zsp_thread.h
    │   └── ...
    └── rt/               # Runtime sources
        ├── zsp_alloc.c
        ├── zsp_component.c
        ├── zsp_thread.c
        └── ...
```

## Usage Example

```python
import zuspec.dataclasses as zdc
from zuspec.be.sw import CGenerator, CValidator, CCompiler, TestRunner
from pathlib import Path

@zdc.dataclass
class MyC(zdc.Component):
    def hello(self):
        print("Hello")

# 1. Build datamodel
dm_ctxt = zdc.DataModelFactory().build(MyC)

# 2. Validate
validator = CValidator()
assert validator.validate(dm_ctxt)

# 3. Generate C code
generator = CGenerator(output_dir=Path("/tmp/output"))
sources = generator.generate(dm_ctxt)

# 4. Compile
compiler = CCompiler(output_dir=Path("/tmp/output"))
result = compiler.compile(sources, Path("/tmp/output/test"))
assert result.success

# 5. Run
runner = TestRunner()
test_result = runner.run(Path("/tmp/output/test"), expected_output="Hello")
assert test_result.passed
```

## Generated Code Example

For the `MyC` component above, the generator produces:

**myc.h:**
```c
#ifndef INCLUDED_MYC_H
#define INCLUDED_MYC_H

#include <stdio.h>
#include <stdint.h>
#include "zsp_component.h"
#include "zsp_init_ctxt.h"

struct MyC;

typedef struct MyC {
    zsp_component_t base;
} MyC;

void MyC_init(
    zsp_init_ctxt_t *ctxt,
    MyC *self,
    const char *name,
    zsp_component_t *parent);

void MyC_hello(MyC *self);

#endif /* INCLUDED_MYC_H */
```

**myc.c:**
```c
#include "myc.h"
#include "zsp_init_ctxt.h"

void MyC_init(
    zsp_init_ctxt_t *ctxt,
    MyC *self,
    const char *name,
    zsp_component_t *parent) {
    zsp_component_init(ctxt, &self->base, name, parent);
}

void MyC_hello(MyC *self) {
    fprintf(stdout, "Hello\n");
}
```

**main.c:**
```c
#include <stdio.h>
#include <stdlib.h>
#include "zsp_alloc.h"
#include "zsp_init_ctxt.h"
#include "myc.h"

int main(int argc, char **argv) {
    zsp_alloc_t alloc;
    zsp_alloc_malloc_init(&alloc);

    zsp_init_ctxt_t ctxt;
    ctxt.alloc = &alloc;

    MyC myc;
    MyC_init(&ctxt, &myc, "myc", NULL);
    MyC_hello(&myc);

    return 0;
}
```
