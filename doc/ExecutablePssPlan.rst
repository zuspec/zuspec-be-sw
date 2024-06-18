
# Core code structure
- Co-routines for actions and exec blocks
- Functions default to blocking (non-coroutine)
- Component-tree structure
- 

# Activity support
- if/else
- match
- repeat

##
- Component DS and init
  - 
  - exec_init_down / exec_init_up as static-virtual methods
  - Assume static knowledge of inheritance relationships
  -

## Phase 1

Goals:
- Properly translate and execute non-blocking code 
  - Functions call and return
  - if/else 
  - match
  - repeat (?)
    - requires support for scope-local variables 
- Support ref-counted object handles with destructors
- Transparent address spaces with non-allocatable regions
  - Implies a strategy for 
- Register-component handles
- Register-component ref handles
- Register access via blocking target functions
- Initial support for actions -- maybe just atomic actions?

.. list-table:: Development Tasks
    :header-rows: 1

    * - Item
      - Description
      - Status
    * - abc
      - asd
      - Done

## Phase 2

Goals:
- Support for blocking target functions (enables Python and SV integrations)
- Support for registering transparent allocatable regions
- Support for 


