
Multi-executor streams of actions are partitioned into per-executor queues
of action-traversal, synchronization, and local-parallel execution directives.

Execution is always assumed to start and end with the default/primary core. 
Non-primary cores must wait for the primary core to pass its initial 
synchronization point before executing any behavior. They must notify
the primary core when their execution is complete.

# Synchronization mechanism
At an absract level, tests implement synchronization via the following API
- wait(exec_id, target_exec_id, target_exec_point_id)
- notify(exec_id, exec_point_id)

## Wait
Wait is called to ensure that the designated executor has reached or passed
the specified execution point. The specified executor ID is that of the
executor to monitor. 

## Notify
Notify is called to update an executor's execution point ID. Doing so 
may cause other executors to unblock. The specified executor ID is that of
the executor whose execution-point ID is being updated.

A core assumption is that implementations of wait/notify can always identify
the executor of the caller. In this sense, passing the executor ID to
'notify' is redundant.

# A bare-metal implementation



