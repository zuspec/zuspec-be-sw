
# Computing Addresses

## Address Handle
- Represented as a struct combining intptr_t and offset basis
struct addr_handle_t {
    intptr_t                addr;
    int32_t                 region;
}

addr is an offset within the specified region. Region is an index
into the array of region accessors, which 

- Stores 