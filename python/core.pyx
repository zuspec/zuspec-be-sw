
import os
import ctypes
from zsp_be_sw cimport decl
from libc.stdint cimport intptr_t

cdef Factory _inst = None

cdef class Factory(object):

    cpdef void init(self, dm_core.Factory dmgr):
        self._hndl.init(dmgr._hndl.getDebugMgr())

    cpdef Output mkFileOutput(self, path):
        cdef decl.IOutput *hndl = self._hndl.mkFileOutput(path.encode())
        return Output.mk(hndl)

    @staticmethod
    def inst():
        cdef Factory factory
        global _inst

        if _inst is None:
            ext_dir = os.path.dirname(os.path.abspath(__file__))

            core_lib = os.path.join(ext_dir, "libzuspec-be-sw.so")

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

