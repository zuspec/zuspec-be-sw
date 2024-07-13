/*
 * TaskGenerateExecModelExecScopeB.cpp
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
#include "OutputStr.h"
#include "TaskCheckExecHasLoop.h"
#include "TaskCheckIsExecBlocking.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExecScopeB.h"
#include "TaskGenerateExecModelExecScopeNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelExecScopeB::TaskGenerateExecModelExecScopeB(
        TaskGenerateExecModel       *gen,
        IGenRefExpr                 *refgen,
        IOutput                     *out_h,
        IOutput                     *out_c) : 
        m_gen(gen), m_refgen(m_refgen), m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelExecScopeB", gen->getDebugMgr());
}

TaskGenerateExecModelExecScopeB::~TaskGenerateExecModelExecScopeB() {

}

void TaskGenerateExecModelExecScopeB::generate(arl::dm::ITypeProcStmtScope *t) {
    DEBUG_ENTER("generate");
    OutputStr out_c(m_out_c->ind());
    OutputStr out_h(m_out_h->ind());
    m_depth = 0;
    m_out_c_s.push_back(&out_c);
    m_out_h_s.push_back(&out_h);
    t->accept(m_this);
    m_out_c_s.pop_back();
    m_out_h_s.pop_back();
    m_out_c->writes(out_c.getValue());
    m_out_h->writes(out_h.getValue());
    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelExecScopeB::visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *t) {
    DEBUG_ENTER("visitTypeProcStmtScope");
    m_idx = 0;
    TaskCheckIsExecBlocking is_b(m_gen->getDebugMgr(), m_gen->isTargetImpBlocking());
    bool has_loop = TaskCheckExecHasLoop().check(t);

    if (is_b.check(t)) {
        OutputStr out_h(m_out_h->ind());
        OutputStr out_c(m_out_c->ind());

        out_h.println("typedef struct exec_%p_s {", t);
        out_h.inc_ind();
        out_h.println("zsp_rt_task_t task;");

        out_c.println("zsp_rt_task_t *exec_%p(%s_t *actor, exec_%p_t *this_s) {",
            t,
            m_gen->getActorName().c_str(),
            t);
        out_c.inc_ind();
        out_c.println("zsp_rt_task_t *ret = 0;");
        if (has_loop) {
            out_c.println("bool re_eval;");
            out_c.println("do {");
            out_c.inc_ind();
            out_c.println("re_eval = false;");
        }
        out_c.println("switch (this_s->task.idx) {");
        out_c.inc_ind();


        m_out_c_s.push_back(&out_c);
        m_out_h_s.push_back(&out_h);
        for (std::vector<arl::dm::ITypeProcStmtUP>::const_iterator 
            it=t->getStatements().begin();
            it!=t->getStatements().end(); it++) {
            out_c.println("case %d: {", m_idx++);
            out_c.inc_ind();
            out_c.println("this_s->task.idx++;");

            if (is_b.check(it->get())) {
                (*it)->accept(m_this);
            } else {
                TaskGenerateExecModelExecScopeNB(
                    m_gen, 
                    m_refgen, 
                    &out_c).generate(it->get(), false);
            }

            out_c.dec_ind();
            out_c.println("}");
        }
        m_out_c_s.pop_back();
        m_out_h_s.pop_back();

        out_h.dec_ind();
        out_h.println("} exec_%p_t;", t);


        out_c.dec_ind();
        out_c.println("}");

        if (has_loop) {
            out_c.dec_ind();
            out_c.println("} while (re_eval);");
        }

        out_c.println("return ret;");
        out_c.dec_ind();
        out_c.println("}");

        m_out_h_s.back()->writes(out_h.getValue());
        m_out_c_s.back()->writes(out_c.getValue());
    } else {
        // This will always be an interior scope
        TaskGenerateExecModelExecScopeNB(
            m_gen, 
            m_refgen, 
            m_out_c_s.back()).generate(t, false);
    }

    DEBUG_LEAVE("visitTypeProcStmtScope");
}

void TaskGenerateExecModelExecScopeB::visitTypeProcStmtYield(arl::dm::ITypeProcStmtYield *t) {
    DEBUG_ENTER("visitTypeProcStmtYield");
    m_out_c_s.back()->println("ret = &this_s->task;");
    m_out_c_s.back()->println("break;");
    DEBUG_LEAVE("visitTypeProcStmtYield");
}

dmgr::IDebug *TaskGenerateExecModelExecScopeB::m_dbg = 0;

}
}
}
