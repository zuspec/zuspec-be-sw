
import ctypes
from zsp_be_sw cimport decl
cimport debug_mgr.core as dm_core


cdef class Factory(object):
    cdef decl.IFactory      *_hndl

    cpdef void init(self, dm_core.Factory dmgr)

