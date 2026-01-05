
# Mapping

## Core requirements
- Method parameters and return types are given types
- 

## Method mapping
- 'print' to print in the Zuspec API. Must convert format strings
  to appropriate format string + parameters form for C

## Data Types
Composite types support inheritance. Class and Component support 
virtual methods. Struct does not, but this is caught upstream.

Use containment to express inheritance on both type (method) and
data side:

```c
typedef struct my_c_s {
  zsp_component_t     base;
} my_c_t;
```

Use macros to 'cast' to base types instead of using dotted references
and/or inline casts. For example:


## Component
`zdc.Component` maps to a C struct with zsp_component_t as a base. The
derived type has function handles for all methods. The initialization
code for the C type will perform additional work in the future. 

## Time 

The timebase implements time as a single integer denominated in its 
resolution time unit -- for example 1ps. Time with unit must be
represented as a two-component struct:

```c
typedef struct zsp_time_s {
    uint64_t   amt;
    int32_t    unit; // Use ZSP constants for unit
} zsp_time_t;
```

This should allow time amt+unit to be easily passed by value to functions.

## Timebase

The timebase is a unified time-aware thread scheduler that replaces the 
original simple scheduler. It manages simulation time and thread scheduling
in a single structure.

### Key Features

- **Single integer time representation**: Time is stored internally as a 
  single `uint64_t` in the resolution unit (e.g., picoseconds) for compute
  efficiency.

- **Configurable resolution**: Timebase resolution can be set during 
  initialization (S, MS, US, NS, PS, FS).

- **Min-heap event queue**: Uses a min-heap for O(log n) event insertion
  and O(1) peek for efficient time-ordered scheduling.

- **Thread suspension**: Threads can suspend for a specified duration using
  `zsp_timebase_wait()`.

### Usage

```c
#include "zsp_timebase.h"

// Create timebase with nanosecond resolution
zsp_timebase_t tb;
zsp_timebase_init(&tb, &alloc, ZSP_TIME_NS);

// Create a thread
zsp_thread_t *t = zsp_timebase_thread_create(&tb, &my_task, ZSP_THREAD_FLAGS_NONE);

// Run simulation until 1 microsecond
zsp_timebase_run_until(&tb, ZSP_TIME_US(1));

// Inside a task - wait for 100ns
zsp_timebase_wait(thread, ZSP_TIME_NS(100));

// Clean up
zsp_timebase_thread_free(t);
zsp_timebase_destroy(&tb);
```

### Component Initialization with Timebase

When initializing a component, a timebase can be specified via the 
`zsp_init_ctxt_t` structure:

```c
zsp_init_ctxt_t ctxt;
ctxt.alloc = &alloc;
ctxt.timebase = &tb;  // Timebase for this component tree

MyComponent_init(&ctxt, &comp, "comp", NULL);
```

# Ports, Exports, and Binds

A port is an API consumer. It is implemented as a pointer to an 
implementation. An export provides an implementation of an API.

APIs supported by Ports and Exports are protocol classes that 
define a pure API with no data.

API classes are implemented as a struct that defines the APIs
and holds a reference to a context handle that is passed to the
APIs. Typically this context handle represents the 'self' or 'this'
handle.


```python3
from typing import Protocol

class MemIF(Protocol):
    async def write(self, addr : zdc.uint64_t, data : zdc.uint64_t): ...
    async def read(self, addr : zdc.uint64_t) -> zdc.uint64_t: ...
```

This API has an implementation similar to the following:

```c

typedef struct MemIF_s {
  void      *self;
  zsp_frame_t *(write)(zsp_thread_t *, int, va_list *args);
  zsp_frame_t *(read)(zsp_thread_t *, int, va_list *args);
} MemIF_t;

```

```python3
@zdc.dataclass
class MyC1(zdc.Component):
    memif : MemIF = zdc.port()

```

This should result in similar C code:

```c
typedef struct MyC1_s {
    zdc_component_t   base;
    MemIF             *memif;
} MyC1_t;
```

```python3
@zdc.dataclass
class MyC2(zdc.Component):
    memif : MemIF = zdc.export()

```

This should result in similar C code:

```c
typedef struct MyC2_s {
    zdc_component_t   base;
    MemIF             memif;
} MyC2_t;
```

Binding involves linking the two bound objects. In this case,
this means having the port point to the export.

```python3
@zdc.dataclass
class Top(zdc.Component):
  c1 : MyC1 = zdc.field()
  c2 : MyC2 = zdc.field()

  def __bind__(self): return {
    self.c1.memif : self.c2.memif
  }
```

```c
void Top__bind(Top *self) {
    // Call bind of sub-components
    self->c1.memif = &self->c2.memif
}
```

Binding of exports within a function is a bit different. In that
case, it associates methods and context with the export. For example:

```python3
@zdc.dataclass
class MyC2(zdc.Component):
    memif : MemIF = zdc.export()

    def __bind__(self): return {
        self.memif.read = self.read,
        self.memif.write = self.write
    }

    async def read(self, addr : zdc.uint64_t) -> zdc.uint64_t:
        # Implementation

    async def write(self, addr : zdc.uint64_t, data : zdc.uint64_t):
        # Implementation

```

```c
void MyC2__bind(MyC2 *self) {
    // Call bind of sub-components
    self->memif.self = self;
    self->memif.write = // handle to vtable entry for write
    self->memif.read = // handle to vtable entry for read
}
```


