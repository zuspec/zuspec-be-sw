
# Executors and Memory Access

Memory-access efficiency is critical. However, PSS allows users to customize
the implementation of memory access.

An executor array is always setup. Each executor has a virtual 
function table with handles either to the default memory access
methods or the user-customized ones.


If no executor in the model takes advantage of this ability to override
implementation of a memory-access method, then the most-efficient 
route (static inline method) will be used. 

