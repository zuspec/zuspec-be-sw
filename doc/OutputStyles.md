
There are two key output styles:
- Dynamic -- driven by an elaborated graph description
- Static  -- driven by a procedural code description and/or an unelaborated graph description
  - An unelaborated graph description requires further exploration

# Static Realization Translation
- Need some form of 'export' to mark the functions that must be callable from outside
- Starting with the root function(s)
  - Add to the 'translate' list
  - Could choose to interpret 'root' as equivalent to 'export' in this case
- Process function, looking for
  - Calls to other functions
  - References to the active executor. 


## Function Types
- Exported PSS functions
- Non-exported PSS functions (ie only called by another PSS function or action)
- Component context functions

## Component Functions
- Component functions are context functions. Each component with context functions
  must be represented by a vtable and associated data (?). Since this is expected
  to be the minor case, we'll want to compress the lookup table.
- Component context functions accept the context data structure as the first 
  parameter.

## Executor Context
- Querying the executor context from an exported function is asking an identity question:
  Which core is this code running on? This implies that a key part of the test ABI is
  to return a per-core data pointer (eg TLS, CLS, etc)
- 

# Blocking Functions

