/*
 * CustomGenImportCall.cpp
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
#include "CustomGenImportCall.h"
#include "TaskGenerateExprNB.h"


namespace zsp {
namespace be {
namespace sw {


CustomGenImportCall::CustomGenImportCall(dmgr::IDebugMgr *dmgr) 
    : TaskGenerateExecModelCustomGenBase(dmgr) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::CustomGenImportCall", dmgr);
}

CustomGenImportCall::~CustomGenImportCall() {

}

void CustomGenImportCall::genExprMethodCallStaticB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) { 
    DEBUG_ENTER("genExprMethodCallStaticB");

    std::string fname = call->getTarget()->name();
    if (fname.rfind("::") != -1) {
        fname = fname.substr(fname.rfind("::")+2);
    }

    out->write("ret = zsp_thread_call(thread, __locals->__api->%s, __locals->__api", fname.c_str());

    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
        it=call->getParameters().begin();
        it!=call->getParameters().end(); it++) {
        out->write(", ");
        TaskGenerateExprNB(ctxt, refgen, out).generate(it->get());
    }
    out->write(");\n");
    out->println("if (ret) break;");

    DEBUG_LEAVE("genExprMethodCallStaticB");
}

void CustomGenImportCall::genExprMethodCallStaticNB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) { 
    DEBUG_ENTER("genExprMethodCallStaticNB %s", call->getTarget()->name().c_str());

    std::string fname = call->getTarget()->name();
    if (fname.rfind("::") != -1) {
        fname = fname.substr(fname.rfind("::")+2);
    }

    out->write("__api->%s((zsp_api_t *)__api", fname.c_str());

    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
        it=call->getParameters().begin();
        it!=call->getParameters().end(); it++) {
        out->write(", ");
        TaskGenerateExprNB(ctxt, refgen, out).generate(it->get());
    }
    out->write(")");

    DEBUG_LEAVE("genExprMethodCallStaticNB");
}

void CustomGenImportCall::genExprMethodCallContextB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) { 
    DEBUG_ENTER("genExprMethodCallContextB");

    DEBUG_LEAVE("genExprMethodCallContextB");
}

void CustomGenImportCall::genExprMethodCallContextNB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) { 
    DEBUG_ENTER("genExprMethodCallContextNB");

    DEBUG_LEAVE("genExprMethodCallContextNB");
}

}
}
}
