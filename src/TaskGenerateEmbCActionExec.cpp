/*
 * TaskGenerateEmbCActionExec.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include "TaskGenerateEmbCActionExec.h"
#include "TaskGenerateEmbCExpr.h"
#include "TaskGenerateEmbCProcScope.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCActionExec::TaskGenerateEmbCActionExec(
    dmgr::IDebugMgr             *dmgr,
    NameMap                     *name_m,
    IOutput                     *out_c) : 
        m_dmgr(dmgr), m_out_c(out_c), m_name_m(name_m) {
    DEBUG_INIT("TaskGenerateEmbCActionExec", dmgr);

}

TaskGenerateEmbCActionExec::~TaskGenerateEmbCActionExec() {

}

void TaskGenerateEmbCActionExec::generate(
        arl::dm::IDataTypeAction    *action_t) {
    for (std::vector<arl::dm::ITypeExecUP>::const_iterator
        it=action_t->getExecs(arl::dm::ExecKindT::Body).begin();
        it!=action_t->getExecs(arl::dm::ExecKindT::Body).end(); it++) {
        (*it)->accept(m_this);
    }

    // Generate the function outline for the exec block
    m_out_c->println("void action_%s_exec(%s *ctx) {",
        m_name_m->getName(action_t).c_str(),
        m_name_m->getName(action_t).c_str());
    m_out_c->inc_ind();

    // TODO:
    TaskGenerateEmbCExpr expr_gen(0);
    expr_gen.setActivePref("ctx", true);
    // TODO:
    TaskGenerateEmbCProcScope scope_gen(
        0,
        m_out_c,
        &expr_gen);
    
    for (std::vector<arl::dm::ITypeExecProc *>::const_iterator
        body_it=m_execs.begin();
        body_it!=m_execs.end(); body_it++) {
        // Isolate different exec body blocks
        if (m_execs.size() > 1) {
            m_out_c->println("{");
            m_out_c->inc_ind();
        }

        scope_gen.generate(
            action_t,
            (*body_it)->getBody());
        
        if (m_execs.size() > 1) {
            m_out_c->dec_ind();
            m_out_c->println("}");
        }
    }

    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("");
}

void TaskGenerateEmbCActionExec::visitTypeExecProc(arl::dm::ITypeExecProc *e) {
    m_execs.push_back(e);
}

dmgr::IDebug *TaskGenerateEmbCActionExec::m_dbg = 0;

}
}
}
