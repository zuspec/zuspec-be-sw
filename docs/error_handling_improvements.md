# Error Handling Improvements

## Summary

Improved robustness of code generators and DataModelFactory by replacing silent failures with clear error messages. The philosophy is: **better to fail early with a clear error than silently produce incorrect code**.

## Changes Made

### 1. DataModelFactory (`data_model_factory.py`)

#### Source Code Retrieval
- **Before**: Silently caught `OSError` and returned empty body
- **After**: Raises `RuntimeError` with explanation:
  ```
  Cannot retrieve source code for class 'ClassName' method 'method_name'. 
  This typically happens when classes are defined in string literals passed to exec() 
  or in interactive sessions. Define your classes in a proper .py module file instead.
  ```

#### __bind__ Method Evaluation
- **Before**: Silently caught all exceptions and returned empty bind map
- **After**: Raises `RuntimeError` with guidance:
  ```
  Failed to evaluate __bind__ method for class 'ClassName': <error details>
  The __bind__ method should return a dict mapping port/export expressions. 
  Example: return {self.producer.output: self.consumer.input}
  ```

#### Type Hints Failures
- **Before**: Silent `except Exception: pass`
- **After**: Added comments explaining why failure is acceptable:
  ```python
  # get_type_hints can fail due to forward references or missing imports
  # This is acceptable - we'll just work without type hints
  ```

### 2. C Generator (`c_generator.py`)

#### Async Method Generation
- **Before**: Returned stub comment `/* async method X - no body in datamodel */`
- **After**: Raises `RuntimeError` with specific error based on failure mode:
  - No datamodel body and no source: "method body is not available in datamodel"
  - OSError from inspect: "source code is not available" (same as DataModelFactory)
  - Parsing errors: "failed to parse source code"

### 3. DmAsyncMethodGenerator (`dm_async_generator.py`)

#### Empty Function Body
- **Added**: Validation at entry to `generate()`:
  ```python
  if not func.body:
      raise ValueError(
          f"Cannot generate async method '{self.method_name}': function body is empty. "
          f"Ensure the datamodel was built with proper source code available."
      )
  ```

#### Unsupported Await Expressions
- **Before**: Returned `"zsp_timebase_yield(thread);"`  as generic fallback
- **After**: Raises `ValueError` with helpful guidance:
  ```
  Unsupported await expression in 'method_name': await some_method(). 
  Supported: await self.wait(time), await port.put(data), await port.get(). 
  For other async operations, ensure they are TLM channel operations on ports.
  ```

#### Unsupported Statements
- **Before**: Returned `f"/* unsupported stmt: {type} */"`
- **After**: Raises `ValueError`:
  ```
  Unsupported statement type in 'method_name': StmtIf. 
  Supported statements: assignments, expressions, return, pass, for loops. 
  Add support for additional statement types if needed.
  ```

#### Unsupported For Loops
- **Before**: Returned `"/* unsupported for loop over {type} */"`
- **After**: Raises `ValueError`:
  ```
  Unsupported for loop in 'method_name': iterating over ExprList. 
  Currently only 'for x in range(...)' loops are supported. 
  Use range() for numeric iteration or implement support for other iterables.
  ```

#### Bug Fix
- Fixed `_is_channel_port()` which was returning a string instead of boolean

### 4. New Feature: Async Method Calls

Added support for calling other async methods from within async methods:
```python
async def method_a(self):
    await self.method_b()  # Now supported!
```

Generates:
```c
ret = zsp_timebase_call(thread, &Component_method_b_task, locals->self);
```

## User Expectations

### Component Classes
1. **Define classes in .py module files**, not in:
   - String literals passed to `exec()`
   - Interactive Python sessions (`python -c`)
   - REPL environments

2. **__bind__ method must return a dict** mapping port/export references:
   ```python
   def __bind__(self):
       return {
           self.producer.output: self.consumer.input,
           self.component.port: self.channel.get,
       }
   ```

### Async Methods
1. **Supported await expressions**:
   - `await self.wait(time)` - wait for time
   - `await port.put(data)` - TLM channel put
   - `await port.get()` - TLM channel get
   - `await self.other_async_method()` - call another async method

2. **Supported statements in async methods**:
   - Assignments: `x = value`
   - Expression statements: `self.count += 1`
   - Return statements: `return value`
   - Pass statements: `pass`
   - For loops over range: `for i in range(10):`

3. **Unsupported** (will raise clear errors):
   - If statements (not yet implemented)
   - While loops (not yet implemented)
   - Try/except (not yet implemented)
   - Awaiting arbitrary functions (only self.wait, port.put/get, self.method)

## Testing

All existing tests pass:
- `tests/unit/test_tlm_channel_codegen.py` - 8/8 passed
- `tests/unit/test_async_port_perf.py` - 6/6 passed

Performance benchmarks still show 2.6x speedup over SystemC.

## Benefits

1. **Faster debugging**: Errors caught at code generation time, not compilation time
2. **Clear guidance**: Error messages explain what's wrong and how to fix it
3. **Prevents silent failures**: No more mysterious empty stubs or comments in generated code
4. **Better maintainability**: Explicit error messages document limitations
