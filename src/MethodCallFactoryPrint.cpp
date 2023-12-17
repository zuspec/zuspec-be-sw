/*
 * MethodCallFactoryPrint.cpp
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
#include "MethodCallFactoryPrint.h"


namespace zsp {
namespace be {
namespace sw {


MethodCallFactoryPrint::MethodCallFactoryPrint(dmgr::IDebugMgr *dmgr) {
    DEBUG_INIT("zsp::be::sw::MethodCallFactoryPrint", dmgr);
}

MethodCallFactoryPrint::~MethodCallFactoryPrint() {

}

vsc::dm::ITypeExpr *MethodCallFactoryPrint::mkCallContext(
        IContext                            *ctxt,
        arl::dm::ITypeExprMethodCallContext *call) {
    vsc::dm::ITypeExpr *ret = 0;
    DEBUG_ENTER("mkCallContext");


    DEBUG_LEAVE("mkCallContext");
    return ret;
}

vsc::dm::ITypeExpr *MethodCallFactoryPrint::mkCallStatic(
        IContext                            *ctxt,
        arl::dm::ITypeExprMethodCallStatic  *call) {
    vsc::dm::ITypeExpr *ret = 0;
    DEBUG_ENTER("mkCallStatic");
    std::vector<vsc::dm::ITypeExpr *> params;
    params.push_back(ctxt->ctxt()->mkTypeExprVal(
        ctxt->ctxt()->mkValRefStr("Hello"))
    );

    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
        it=call->getParameters().begin()+1;
        it!=call->getParameters().end(); it++) {
        params.push_back(ctxt->ctxt()->mkTypeExprRef(it->get(), false));
    }

    ret = ctxt->ctxt()->mkTypeExprMethodCallStatic(
        ctxt->getBackendFunction(BackendFunctions::Printf),
        params,
        true
    );

    DEBUG_LEAVE("mkCallStatic");
    return ret;
}

dmgr::IDebug *MethodCallFactoryPrint::m_dbg = 0;

}
}
}
