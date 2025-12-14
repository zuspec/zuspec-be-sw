
# Mapping

## Core requirements
- Method parameters and return types are given types
- 

## Method mapping
- 'print' to print in the Zuspec API. Must convert format strings
  to appropriate format string + parameters form for C

## Data Types
Composite types support inheritance. Class and Component support 
virtual methods. Struct does not, but this is caught upstream.

Use containment to express inheritance on both type (method) and
data side:

```c
typedef struct my_c_s {
  zsp_component_t     base;
} my_c_t;
```

Use macros to 'cast' to base types instead of using dotted references
and/or inline casts. For example:


## Component
`zdc.Component` maps to a C struct with zsp_component_t as a base. The
derived type has function handles for all methods. The initialization
code for the C type will perform additional work in the future. 

