/*
 * TaskGenerateExecModelMemRwCall.cpp
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
#include "zsp/arl/dm/impl/TaskGetTypeBitWidth.h"
#include "zsp/arl/dm/impl/TaskIsPackedStruct.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelMemRwCall.h"
#include "TaskGenerateExprNB.h"
#include "TaskGenerateExecModelExprParamNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelMemRwCall::TaskGenerateExecModelMemRwCall(
    dmgr::IDebugMgr *dmgr) : TaskGenerateExecModelCustomGenBase(dmgr) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelMemRwCall", dmgr);
}

TaskGenerateExecModelMemRwCall::~TaskGenerateExecModelMemRwCall() {

}

void TaskGenerateExecModelMemRwCall::genExprMethodCallStaticB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) {
    DEBUG_ENTER("genExecMethodCallStaticB");

    DEBUG_LEAVE("genExecMethodCallStaticB");
}

void TaskGenerateExecModelMemRwCall::genExprMethodCallStaticNB(
        IContext                            *ctxt,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) {
    DEBUG_ENTER("genExecMethodCallStaticNB");
    const std::string &name = call->getTarget()->name();
    std::string fname;
    int32_t idx = name.find("::");

    fname = "zsp_rt_";
    fname += name.substr(idx+2);

    out->write("%s((void *)((", fname.c_str());
    TaskGenerateExecModelExprParamNB(ctxt, refgen, out).generate(
        call->getParameters().at(0).get());
    out->write(")->store->hndl+(");
    TaskGenerateExecModelExprParamNB(ctxt, refgen, out).generate(
        call->getParameters().at(0).get());
    out->write(")->offset)");

    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
        it=call->getParameters().begin()+1;
        it!=call->getParameters().end(); it++) {
        out->write(", ");
        TaskGenerateExecModelExprParamNB(ctxt, refgen, out).generate(it->get());
    }

    out->write(")");



    DEBUG_LEAVE("genExecMethodCallStaticNB");
}

}
}
}
