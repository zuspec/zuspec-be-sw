/*
 * TaskGenerateExecModelRegRwCall.cpp
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
#include "TaskGenerateExecModelRegRwCall.h"
#include "TaskGenerateExecModelExprNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelRegRwCall::TaskGenerateExecModelRegRwCall(
    dmgr::IDebugMgr *dmgr) : TaskGenerateExecModelCustomGenBase(dmgr) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelRegRwCall", dmgr);
}

TaskGenerateExecModelRegRwCall::~TaskGenerateExecModelRegRwCall() {

}

void TaskGenerateExecModelRegRwCall::genExprMethodCallContextB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) {
    DEBUG_ENTER("genExprMethodCallContextB");
    DEBUG_LEAVE("genExprMethodCallContextB");
}

void TaskGenerateExecModelRegRwCall::genExprMethodCallContextNB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) {
    DEBUG_ENTER("genExprMethodCallContextNB");
    const std::string &name = call->getTarget()->name();

    // Determine register width
    int32_t width = arl::dm::TaskGetTypeBitWidth().width(
        call->getTarget()->getParameters().at(0)->getDataType());
    bool write = false;
    bool sval = false;
    char func[256];
    
    DEBUG("width: %d", width);

    if (width > 32) {
        width = 64;
    } else if (width > 16) {
        width = 32;
    } else if (width > 8) {
        width = 16;
    } else {
        width = 8;
    }

    if (name.find("write_val") != -1) {
        snprintf(func, sizeof(func), "zsp_rt_write%d", width);
        write = true;
    } else if (name.find("read_val") != -1) {
        snprintf(func, sizeof(func), "zsp_rt_read%d", width);
    } else if (name.find("write") != -1) {
        snprintf(func, sizeof(func), "zsp_rt_write%d", width);
        write = true;
        sval = true;
    } else if (name.find("read") != -1) {
        snprintf(func, sizeof(func), "zsp_rt_read%d", width);
    }

    out->write("%s(&", func);

    TaskGenerateExecModelExprNB(gen, refgen, out).generate(
        call->getContext());
    if (call->getParameters().size()) {
        out->write(", ");
    }

    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
        it=call->getParameters().begin();
        it!=call->getParameters().end(); it++) {
        if (it != call->getParameters().begin()) {
            out->write(", ");
        }
        TaskGenerateExecModelExprNB(gen, refgen, out).generate(it->get());

        if (write && sval && it+1 == call->getParameters().end()) {
            out->write(".val");
        }
    }
    out->write(")");
    DEBUG_LEAVE("genExprMethodCallContextNB");
}

}
}
}
