
import os
import ctypes
from zsp_be_sw cimport decl
from libcpp.vector cimport vector as cpp_vector
from libc.stdint cimport intptr_t
cimport ciostream
cimport debug_mgr.core as dm_core
cimport vsc_dm.decl as vsc_dm_decl
cimport vsc_dm.core as vsc_dm
cimport zsp_arl_dm.core as arl_dm
cimport zsp_arl_dm.decl as arl_dm_decl

cdef Factory _inst = None

cdef class Context(object):

    @staticmethod
    cdef Context mk(decl.IContext *hndl, bool owned=True):
        ret = Context()
        ret._hndl = hndl
        ret._owned = owned
        return ret

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

    cpdef Context mkContext(self, arl_dm.Context ctxt):
        return Context.mk(
            self._hndl.mkContext(ctxt.asContext()),
            True)

    cpdef void generateC(
        self,
        Context ctxt,
        roots,
        csrc,
        pub_h,
        prv_h):
        cdef cpp_vector[vsc_dm_decl.IAcceptP] roots_c
        cdef vsc_dm.ObjBase obj
        cdef ciostream.costream csrc_s = ciostream.costream(csrc)
        cdef ciostream.costream pub_h_s = ciostream.costream(pub_h)
        cdef ciostream.costream prv_h_s = ciostream.costream(prv_h)

        for r in roots:
            obj = <vsc_dm.ObjBase>(r)
            roots_c.push_back(obj._hndl)
        
        self._hndl.generateC(
            ctxt._hndl,
            roots_c, 
            csrc_s.stream(),
            pub_h_s.stream(),
            prv_h_s.stream())

    cpdef void initContextC(self, arl_dm.Context ctxt):
        self._hndl.initContextC(ctxt.asContext())


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
