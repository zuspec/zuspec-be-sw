
# Restrictions
- No hierarchical refs or binds
  - Exception for memory and executor claims 
- No constraints beyond equality
- No implied binds
- 

# Supported Features
- Buffer, State, Stream, Resource objects
  - Matching is completely unconstrained
- Component tree
- Transparent and opaque address spaces
- Opaque address claims
- Register model
- Imported solve and target functions
- Executors
- Activities
  - Replicate

action Atomic {
    input Buf dat_i;
}

action Producer {
    output Buf dat_o;
}

action Compound {

    activity {
        A1: do Atomic;
    }
}

action CompoundUpper {
    activity {
        A1 : do Producer;
        A2 : do Compound;
        bind A1.dat_o A2.A1.dat_i;
    }
}

action Compound_p1 : Compound{
    input Buf       Buf_i_1;

    activity {
        bind A1.dat_i Buf_i_1;
    }
}

## Core Library
- 

# Core Memory Management
- Actions can be stack-allocated, since their lifetime doesn't
  extend beyond that of their parent
- Action handles with refs from above must be heap allocated

# Target Memory Management
- Gen-time selection for how allocated and non-allocated regions
  are managed
  - 


# Phase 1 -- Proof of Life
- Actor interface
- Component tree skeleton w/o data or init
- Compound actions with sequential traversal
- Atomic actions
- Sequenced pre-solve, post-solve, body exec blocks
- Solve and target functions

## Result
- Execution produces a series of call-outs to import functions

# Phase 2 -- Let there be registers
- Component tree skeleton with support for data and init
- Address spaces and non-allocated memory regions
- Register model instances and refs

## Result
- Access memory-mapped registers

# Phase 3 -- Target memory allocation

## Result

# Phase 4 -- Data connections
- Passing data via buffers
- Persistent data in states
- Protected data in resources

## Result
