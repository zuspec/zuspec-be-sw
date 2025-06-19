# Building Async Methods

We transform blocking (ie Target) exec blocks to async methods. This is
done independently of whether anything in the exec block *actually* 
blocks. 

Any *potentially blocking* method will following the pattern of a coroutine:
- Allocate locals space on the thread stack
- Body as a case statement with at least two branches
  - **case 0** - 
  - **default** - Default exit from the coroutine

Exec blocks are processed by the *TaskBuildAsyncScopeGroup* class.
Expressions containing a blocking sub-expression are rewritten 
to distribute evaluation across multiple coroutine phases 
connected by temporary variables.

```pss
int a = read();
```

`read` is a blocking method. That means that this statement must be broken 
up across at least two coroutine scopes:


- **s1** - initiate read
- **s2** - complete read, assigning the result to a temporary, and the temporary to `a`

In this case, the temporary is redundant. In more-complex cases, the temporary 
is required:

```pss
int a = read() + read();
```

- **s1** - initiate read[1]
- **s2** - complete read[1] and save to a temp var. initiate read[2]
- **s3** - complete read[2] and save to a temp var. assign `a = t1 + t2`


## Coroutines

- Scopes designated as task-scope 'enter' or 'leave'
- Target scope specified as an argument
- Notion of a 'thread' scope that has a backref to the outer scope

- Each 'init' scope must acquire enough memory for:
  - Maximum size subscope
  - Maximum parallel threads launched by the 'thread'
  - 

- Each scope has a 'locals' type
  - Scope frame *always* has locals of this type

- Task call must take 

## Activity coroutine function

- thread (built-in)
- idx (built-in)
- self (Action handle)
- activity_ctxt
  - parent_scope (scope for the action to check in with)

