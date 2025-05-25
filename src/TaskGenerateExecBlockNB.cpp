/*
 * TaskGenerateExecBlockNB.cpp
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
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecBlockNB.h"
#include "TaskGenerateExecScopeNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecBlockNB::TaskGenerateExecBlockNB(
        IContext                    *ctxt,
        IGenRefExpr                 *refgen,
        IOutput                     *out) : 
        m_ctxt(ctxt), m_refgen(refgen), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecBlockNB", ctxt->getDebugMgr());
}

TaskGenerateExecBlockNB::~TaskGenerateExecBlockNB() {

}

void TaskGenerateExecBlockNB::generate(
        const std::string                           &fname,
        const std::string                           &tname,
        const std::vector<arl::dm::ITypeExecUP>     &execs) {
    m_out->println("static void %s(zsp_actor_t *actor, %s_t *this_p) {",
        fname.c_str(),
        tname.c_str());
    m_out->inc_ind();

    TaskGenerateExecScopeNB(m_ctxt, m_refgen, m_out).generate(
        execs,
        false
    );

    m_out->dec_ind();
    m_out->println("}");
}

dmgr::IDebug *TaskGenerateExecBlockNB::m_dbg = 0;

}
}
}
