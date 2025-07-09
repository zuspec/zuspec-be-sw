# Active Context

## Current Focus Areas

1. PSS Model Execution
   - Thread and actor management system
   - Async scope implementation
   - Action execution flow
   - Component lifecycle management

2. Register Block Implementation
   - Register model generation
   - Access method implementation
   - Block-level operations
   - Hardware interface simulation

3. Python API Development
   - Model interaction interfaces
   - Component type management
   - Action type support
   - Scheduler implementation

## Recent Work

1. Core Runtime
   - Actor system implementation
   - Thread management
   - Memory management patterns
   - Component hierarchy

2. Code Generation
   - Model generation tasks
   - Action type generation
   - Component structure generation
   - Execution block generation

3. Testing Infrastructure
   - Unit test framework
   - Register model testing
   - Dual register block support
   - Target execution statements

## Active Decisions

1. Memory Management
   - Structured inheritance for type safety
   - Component lifecycle tracking
   - Memory allocation strategies
   - Resource cleanup patterns

2. Threading Model
   - Actor-based execution
   - Async scope grouping
   - Event scheduling
   - Thread synchronization

3. Code Generation
   - Task-based generation approach
   - Type-specific generators
   - Progressive model building
   - Output organization

## Implementation Patterns

1. Bare Metal C Code
   ```c
   // Structural inheritance pattern
   typedef struct s1_s {
       int a;
   } s1_t;

   typedef struct s2_s {
       s1_t        base;
       int         b;
   } s2_t;
   ```

2. Register Blocks
   ```
   component my_reg_block : reg_block_c {
     reg_c<bit[32]>   reg_a;
     reg_c<bit[32]>   reg_b;
   }
   ```

3. Unit Testing
   ```python
   # PSS/Python testing pattern
   pss_top = """
   component test_comp {
       // PSS component definition
   }
   """
   ```

## Next Steps

1. Runtime Enhancement
   - Complete async scope implementation
   - Optimize thread management
   - Enhance actor system
   - Improve memory management

2. Code Generation
   - Refine model generation
   - Enhance register block support
   - Improve action generation
   - Optimize output structure

3. Testing
   - Expand unit test coverage
   - Add integration tests
   - Enhance register testing
   - Implement performance tests

## Key Insights

1. Architecture
   - Component-based design effective for PSS
   - Actor model suits execution needs
   - Task-based generation provides flexibility
   - Type system mapping crucial for Python interface

2. Implementation
   - Bare metal constraints guide patterns
   - Memory management critical for reliability
   - Thread safety requires careful design
   - Code generation needs progressive approach

3. Testing
   - Mixed PSS/Python tests effective
   - Register block testing critical
   - Async behavior needs careful validation
   - Performance testing important for runtime
