
import os
import ctypes
from zsp_be_sw cimport decl
from libcpp.vector cimport vector as cpp_vector
from libc.stdint cimport intptr_t
cimport debug_mgr.core as dm_core
cimport zsp_arl_dm.core as arl_dm
cimport zsp_arl_dm.decl as arl_dm_decl

cdef Factory _inst = None

cdef class Factory(object):

    cpdef void init(self, dm_core.Factory dmgr):
        self._hndl.init(dmgr._hndl.getDebugMgr())

    cpdef GeneratorFunctions mkGeneratorFunctionsThreaded(self):
        return GeneratorFunctions.mk(
            self._hndl.mkGeneratorFunctionsThreaded(),
            True
        )

    cpdef GeneratorEvalIterator mkGeneratorMultiCoreSingleImageEmbCTest(
        self,
        executors,
        int32_t                 dflt_exec,
        Output                  out_h,
        Output                  out_c):
        cdef arl_dm.ModelFieldExecutor exec_dm
        cdef cpp_vector[arl_dm_decl.IModelFieldExecutorP] executors_l

        for e in executors:
            exec_dm = <arl_dm.ModelFieldExecutor>(e)
            executors_l.push_back(exec_dm.asExecutor())

        return GeneratorEvalIterator.mk(
            self._hndl.mkGeneratorMultiCoreSingleImageEmbCTest(
                executors_l,
                dflt_exec,
                out_h._hndl,
                out_c._hndl
            ),
            True
        )


    cpdef Output mkFileOutput(self, path):
        cdef decl.IOutput *hndl = self._hndl.mkFileOutput(path.encode())
        return Output.mk(hndl)

    @staticmethod
    def inst():
        cdef Factory factory
        global _inst

        if _inst is None:
            ext_dir = os.path.dirname(os.path.abspath(__file__))

            core_lib = os.path.join(ext_dir, "libzsp-be-sw.so")

            if not os.path.isfile(core_lib):
                raise Exception("Extension library core \"%s\" doesn't exist" % core_lib)
            so = ctypes.cdll.LoadLibrary(core_lib)

            func = so.zsp_be_sw_getFactory
            func.restype = ctypes.c_void_p

            hndl = <decl.IFactoryP>(<intptr_t>(func()))
            factory = Factory()
            factory._hndl = hndl
            factory.init(dm_core.Factory.inst())
            _inst = factory

        return _inst

cdef class GeneratorEvalIterator(object):

    cpdef void generate(
        self,
        arl_dm.ModelFieldComponentRoot      root,
        arl_dm.ModelEvalIterator            it):
        self._hndl.generate(root.asComponentRoot(), it._hndl)

    @staticmethod
    cdef mk(decl.IGeneratorEvalIterator *hndl, bool owned=True):
        ret = GeneratorEvalIterator()
        ret._hndl = hndl
        ret._owned = owned
        return ret

cdef class GeneratorFunctions(object):

    cpdef void generate(
        self,
        arl_dm.Context                      ctxt,
        funcs,
        inc_c,
        inc_h,
        Output                              out_c,
        Output                              out_h):
        pass
    
    @staticmethod
    cdef mk(decl.IGeneratorFunctions *hndl, bool owned=True):
        ret = GeneratorFunctions()
        ret._hndl = hndl
        ret._owned = owned
        return ret

cdef class Output(object):

    cpdef void close(self):
        self._hndl.close()

    @staticmethod
    cdef Output mk(decl.IOutput *hndl):
        ret = Output()
        ret._hndl = hndl
        return ret
