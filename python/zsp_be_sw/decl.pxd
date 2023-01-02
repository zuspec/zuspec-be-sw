
cimport zsp_arl_dm.decl as arl
cimport debug_mgr.decl as dm

ctypedef IFactory *IFactoryP

cdef extern from "zsp/be/sw/IFactory.h" namespace "zsp::be::sw":
    cdef cppclass IFactory:
        void init(dm.IDebugMgr *dmgr)
        dm.IDebugMgr *getDebugMgr()

