
cimport ciostream
cimport zsp_arl_dm.decl as arl_dm
cimport vsc_dm.decl as vsc_dm_decl
cimport debug_mgr.decl as dm

from libcpp.string cimport string as cpp_string
from libcpp.vector cimport vector as cpp_vector
from libcpp.memory cimport unique_ptr
from libcpp cimport bool
from libc.stdint cimport int32_t
cimport cpython.ref as cpy_ref

ctypedef IFactory *IFactoryP

cdef extern from "zsp/be/sw/IContext.h" namespace "zsp::be::sw":
    cdef cppclass IContext:
        dm.IDebugMgr *getDebugMgr()
        arl_dm.IContext *ctxt()

cdef extern from "zsp/be/sw/IFactory.h" namespace "zsp::be::sw":
    cdef cppclass IFactory:
        void init(dm.IDebugMgr *dmgr)
        dm.IDebugMgr *getDebugMgr()
        IGeneratorFunctions *mkGeneratorFunctionsThreaded()
        IGeneratorEvalIterator *mkGeneratorMultiCoreSingleImageEmbCTest(
            const cpp_vector[arl_dm.IModelFieldExecutorP]   &executors,
            int32_t                                         dflt_exec,
            IOutput                                         *out_h,
            IOutput                                         *out_c)
        IContext *mkContext(arl_dm.IContext *ctxt)
        void generateC(
            IContext                                        *ctxt,
            const cpp_vector[vsc_dm_decl.IAcceptP]          &roots,
            ciostream.ostream                               *csrc,
            ciostream.ostream                               *pub_h,
            ciostream.ostream                               *prv_h)

        void initContextC(arl_dm.IContext                   *ctxt)

        IOutput *mkFileOutput(const cpp_string &path)

cdef extern from "zsp/be/sw/IGeneratorEvalIterator.h" namespace "zsp::be::sw":
    cdef cppclass IGeneratorEvalIterator:
        void generate(
            arl_dm.IModelFieldComponentRoot     *root,
            arl_dm.IModelEvalIterator           *it)

cdef extern from "zsp/be/sw/IGeneratorFunctions.h" namespace "zsp::be::sw":
    cdef cppclass IGeneratorFunctions:
        void generate(
            arl_dm.IContext                                 *ctxt,
            const cpp_vector[arl_dm.IDataTypeFunctionP]     &funcs,
            const cpp_vector[cpp_string]                    &inc_c,
            const cpp_vector[cpp_string]                    &inc_h,
            IOutput                                         *out_c,
            IOutput                                         *out_h)

cdef extern from "zsp/be/sw/IOutput.h" namespace "zsp::be::sw":
    cdef cppclass IOutput:
        void close()

