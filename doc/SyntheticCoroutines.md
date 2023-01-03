
# Requirements
- Max-size any variable-sized data
- No recursion
- Note: this is only necessary for functions that may block. Recursion is
  okay as long as the function doesn't block.

# Approach
- Each function type has a max-sized local-storage block that captures its
  storage requirements and those of any sub-calls. 
- All blocking functions have the same function signature
- The local-storage block covers both parameter passing and local variables.
- Blocking functions are implemented as FSMs, with each case representing
  the code between potential block locations.
- The local-storage block must emulate the return stack.
  - Each call-in saves the caller's function as return address
  - There must be a resume address for the entire coroutine
  -> Co-routines only start because of a call from an action

## Unions
- Local-storage space for blocking calls made in sequence can be reused
- Local-storage space for mutually-exclusive blocking calls can be
  max-sized and shared. For example, multiple branches of if/else

## Root Block
- The root of a coroutine tracks the entry/resume point. 
- Always just pass the coroutine object and let the invoked function
  find its data?


