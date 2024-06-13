
# Standard virtual functions

All (?) objects have a virtual function table used to perform
key functions. All object types have a constructor function
to create an initialize an object

- Component context, flow-object input binding


- Determine bindings for input flow objects, resource claims, and component context
  - How do we capture the possibilities for each?
- Create an action data structure, and any output flow objects
  - Parent action must hold a reference to the action until end-of-scope
  - The constructor accepts bindings for context and inputs
  - The constructor creates output objects

- Execute value-assignment (randomization) flow
- Execute action body -- coroutine
  - Execute steps
  - Execute local clean-up at end-of-scope

- Caller transfers ownership for any 'owned' outputs
- Destructs the action object, cleaning up any objects still owned by the action
- Actions *never* own inputs and claims
- Actions *always* own outputs for the lifetime of the action
- Context action must move outputs before dtor to persist ownership

- In each context, each action claim is bound to one and only one pool
  - don't need to worry about having two views of a set of pools

- Does body need to be virtual?

- Don't think we need to hang onto the action object beyond its body
- Requires 

- Could use unions to represent scopes that do not uniquely exist in time

- Running on an executor means queuing on the executor's task queue
  - How do we wait for completion?
  - Maybe 'run-on-executor' is a wrapper task
  - Can generate different code to execute on a foreign executor

- What about local tasks?
  - Fork 
  - Some parallel tasks will be on the same 
