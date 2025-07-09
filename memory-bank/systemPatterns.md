# System Patterns

## Core Architecture

### Component Hierarchy
1. Base Objects
   - `zsp_object` - Root of all runtime objects
   - `zsp_struct` - Base for structured data types
   - `zsp_component` - Base for PSS components
   - `zsp_actor` - Execution context for components

2. Runtime Management
   - `zsp_model` - Global model context
   - `zsp_thread` - Thread management
   - `zsp_executor` - Action execution engine

### Memory Management
1. Structural Inheritance Pattern
   ```c
   // Base struct listed first in derived struct
   typedef struct base_s {
       int a;
   } base_t;

   typedef struct derived_s {
       base_t      base;
       int         b;
   } derived_t;

   // Access via type casting macros
   #define base(obj) ((base_t *)(obj))
   #define derived(obj) ((derived_t *)(obj))
   ```

2. Component Tree Structure
   - Components form hierarchical relationships
   - Parent-child relationships managed through runtime
   - Memory management follows component lifecycle

## Code Generation Patterns

### Model Generation
1. Task-Based Generation
   - Separate tasks for different generation aspects
   - Progressive model building
   - Type-specific generation tasks

2. Register Block Generation
   ```
   component reg_block : reg_block_c {
     reg_c<bit[32]>   reg_a;
     reg_c<bit[32]>   reg_b;
   }
   ```

### Execution Patterns

1. Async Scope Management
   - Groups of async operations
   - Scope-based execution control
   - Activity scheduling and synchronization

2. Actor System
   - Actor-based concurrency model
   - Message passing between actors
   - State management within actors

## Testing Patterns

1. Unit Test Structure
   ```python
   # PSS code at top of test
   pss_top = """
   component test_comp {
       // PSS component definition
   }
   """
   
   # Python test implementation
   def test_feature():
       # Test implementation
   ```

2. Register Model Testing
   - Block-level testing
   - Access pattern verification
   - Hardware interface simulation

## Integration Patterns

1. Python-C Interface
   - Clean API boundary
   - Type mapping system
   - Error handling propagation

2. Component Integration
   - Standard component interfaces
   - Lifecycle management hooks
   - Resource sharing protocols

## Design Patterns

1. Task Pattern
   - Task classes for specific operations
   - Clear input/output contracts
   - Progress tracking capabilities

2. Generator Pattern
   - Specialized generators for different outputs
   - Consistent generation interface
   - Configuration flexibility

3. Visitor Pattern
   - Used for tree traversal
   - Type-specific processing
   - Separation of algorithms from structures


# Building and Running

## Building the Project
- Once the project has been initialized with IVPM, the project can be built using the following command:
```
% DEBUG=1 ./packages/python/bin/python setup.py build_ext --inplace
```

