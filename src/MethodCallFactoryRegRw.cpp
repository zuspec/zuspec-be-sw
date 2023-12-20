/*
 * MethodCallFactoryRegRw.cpp
 *
 * Copyright 2023 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include "dmgr/impl/DebugMacros.h"
#include "vsc/dm/impl/TaskComputeTypePackedSize.h"
#include "MethodCallFactoryRegRw.h"


namespace zsp {
namespace be {
namespace sw {


MethodCallFactoryRegRw::MethodCallFactoryRegRw(
    dmgr::IDebugMgr         *dmgr,
    bool                    is_write,
    bool                    is_val) : m_is_write(is_write), m_is_val(is_val) {
    DEBUG_INIT("zsp::be::sw::MethodCallFactoryRegRw", dmgr);
}

MethodCallFactoryRegRw::~MethodCallFactoryRegRw() {

}

vsc::dm::ITypeExpr *MethodCallFactoryRegRw::mkCallContext(
        IContext                            *ctxt,
        arl::dm::ITypeExprMethodCallContext *call) {
    vsc::dm::ITypeExpr *ret = 0;
    DEBUG_ENTER("mkCallContext");
    int32_t bit_sz = vsc::dm::TaskComputeTypePackedSize().compute(
        (m_is_write)?call->getTarget()->getParameters().at(0)->getDataType():
            call->getTarget()->getReturnType());
    arl::dm::IDataTypeFunction *rw_func = 0;
    if (bit_sz > 32) {
        rw_func = (m_is_write)?
            ctxt->getBackendFunction(BackendFunctions::Write64):
            ctxt->getBackendFunction(BackendFunctions::Read64);
    } else if (bit_sz > 16) {
        rw_func = (m_is_write)?
            ctxt->getBackendFunction(BackendFunctions::Write32):
            ctxt->getBackendFunction(BackendFunctions::Read32);
    } else if (bit_sz > 8) {
        rw_func = (m_is_write)?
            ctxt->getBackendFunction(BackendFunctions::Write16):
            ctxt->getBackendFunction(BackendFunctions::Read16);
    } else {
        rw_func = (m_is_write)?
            ctxt->getBackendFunction(BackendFunctions::Write8):
            ctxt->getBackendFunction(BackendFunctions::Read8);
    }

    DEBUG("bit_sz: %d", bit_sz);

    std::vector<vsc::dm::ITypeExpr *> params;
    params.push_back(ctxt->ctxt()->mkTypeExprUnary(
        call->getContext(),
        false,
        vsc::dm::UnaryOp::Ptr
    ));

    if (m_is_write) {
        params.push_back(ctxt->ctxt()->mkTypeExprRef(
            call->getParameters().at(0).get(),
            false
        ));
    }

    ret = ctxt->ctxt()->mkTypeExprMethodCallStatic(
        rw_func,
        params,
        true);

    DEBUG_LEAVE("mkCallContext");
    return ret;
}

dmgr::IDebug *MethodCallFactoryRegRw::m_dbg = 0;

}
}
}
