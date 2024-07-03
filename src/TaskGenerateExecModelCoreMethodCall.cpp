/*
 * TaskGenerateExecModelCoreMethodCall.cpp
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
#include "TaskGenerateExecModelExprParamNB.h"
#include "TaskGenerateExecModelCoreMethodCall.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelCoreMethodCall::TaskGenerateExecModelCoreMethodCall(
    dmgr::IDebugMgr                     *dmgr,
    const std::string                   &name,
    int32_t                             cast_offset,
    const std::vector<std::string>      &types) :
    TaskGenerateExecModelCustomGenBase(dmgr),
    m_name(name), m_cast_offset(cast_offset), m_types(types.begin(), types.end()) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelCoreMethodCall", dmgr);
}

TaskGenerateExecModelCoreMethodCall::~TaskGenerateExecModelCoreMethodCall() {

}

void TaskGenerateExecModelCoreMethodCall::genExprMethodCallContextNB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallContext *call) {
    int32_t cast_idx = 0;
    DEBUG_ENTER("genExprMethodCallContextNB");
    out->write("%s((zsp_rt_actor_t *)actor, ", m_name.c_str());

    if (m_cast_offset == 0) {
        out->write("(%s)", m_types.at(cast_idx).c_str());
        cast_idx++;
    }

    TaskGenerateExecModelExprParamNB(gen, refgen, out).generate(call->getContext());

    if (call->getParameters().size()) {
        out->write(", ");
    }

    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
        it=call->getParameters().begin();
        it!=call->getParameters().end(); it++) {
        if (it != call->getParameters().begin()) {
            out->write(", ");
        }
        if (cast_idx < m_types.size()) {
            out->write("(%s)", m_types.at(cast_idx).c_str());
            cast_idx++;
        }
        TaskGenerateExecModelExprParamNB(gen, refgen, out).generate(it->get());
    }

    out->write(")");
    DEBUG_LEAVE("genExprMethodCallContextNB");
}

void TaskGenerateExecModelCoreMethodCall::genExprMethodCallStaticNB(
        TaskGenerateExecModel               *gen,
        IOutput                             *out,
        IGenRefExpr                         *refgen,
        arl::dm::ITypeExprMethodCallStatic  *call) {
    int32_t cast_idx = 0;
    DEBUG_ENTER("genExprMethodCallStaticNB");
    out->write("%s((zsp_rt_actor_t *)actor", m_name.c_str());

    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
        it=call->getParameters().begin();
        it!=call->getParameters().end(); it++) {
        out->write(", ");
        if (cast_idx < m_types.size()) {
            out->write("(%s)", m_types.at(cast_idx).c_str());
            cast_idx++;
        }
        TaskGenerateExecModelExprParamNB(gen, refgen, out).generate(it->get());
    }

    out->write(")");
    DEBUG_LEAVE("genExprMethodCallStaticNB");
}


}
}
}
