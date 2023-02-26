
import ctypes
from zsp_be_sw cimport decl
cimport zsp_arl_dm.core as arl_dm
cimport debug_mgr.core as dm_core
from libcpp cimport bool
from libc.stdint cimport int32_t


cdef class Factory(object):
    cdef decl.IFactory      *_hndl

    cpdef void init(self, dm_core.Factory dmgr)

    cpdef GeneratorFunctions mkGeneratorFunctionsThreaded(self)

    cpdef GeneratorEvalIterator mkGeneratorMultiCoreSingleImageEmbCTest(
        self,
        executors,
        int32_t                 dflt_exec,
        Output                  out_h,
        Output                  out_c)

    cpdef Output mkFileOutput(self, path)

cdef GeneratorEvalIterator(object):
    cdef decl.IGeneratorEvalIterator        *_hndl
    cdef bool                               _owned

    cpdef void generate(
        self,
        arl_dm.ModelFieldComponentRoot      root,
        arl_dm.ModelEvalIterator            it)

    @staticmethod
    cdef mk(decl.IGeneratorEvalIterator *hndl, bool owned=*)

cdef GeneratorFunctions(object):
    cdef decl.IGeneratorFunctions           *_hndl
    cdef bool                               _owned

    cpdef void generate(
        self,
        arl_dm.mkContext                    ctxt,
        funcs,
        inc_c,
        inc_h,
        Output                              out_c,
        Output                              out_h)
    
    @staticmethod
    cdef mk(decl.IGeneratorFunctions *hndl, bool owned=*)


cdef Output(object):
    cdef decl.IOutput                       *_hndl

    cpdef void close(self)

    @staticmethod
    cdef Output mk(decl.IOutput *hndl)


