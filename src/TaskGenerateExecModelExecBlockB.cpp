/*
 * TaskGenerateExecModelExecBlockB.cpp
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
#include "OutputStr.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExecBlockB.h"
#include "TaskGenerateExecModelExecScopeB.h"
#include "TaskGenerateExecScopeNB.h"
#include "TaskCheckIsExecBlocking.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelExecBlockB::TaskGenerateExecModelExecBlockB(
    TaskGenerateExecModel           *gen,
    IGenRefExpr                     *refgen,
    IOutput                         *out_h,
    IOutput                         *out_c) :
    m_gen(gen), m_refgen(refgen), m_out_h(out_h), m_out_c(out_c) {

}

TaskGenerateExecModelExecBlockB::~TaskGenerateExecModelExecBlockB() {

}

void TaskGenerateExecModelExecBlockB::generate(
        const std::string                           &fname,
        const std::string                           &tname,
        const std::vector<arl::dm::ITypeExecUP>     &execs) {
    int32_t idx = 0;

    m_out_c->println("static void %s_init(struct %s_s *actor, %s *this_p) {",
        fname.c_str(),
        m_gen->getActorName().c_str(),
        tname.c_str());
    m_out_c->inc_ind();
    m_out_c->println("this_p->task.func = (zsp_rt_task_f)&%s_run;", fname.c_str());
    m_out_c->dec_ind();
    m_out_c->println("}");

    TaskCheckIsExecBlocking is_b(
        m_gen->getDebugMgr(), 
        m_gen->isTargetImpBlocking());

    // First, go through and define the functions for blocking sub-
    for (std::vector<arl::dm::ITypeExecUP>::const_iterator
            it=execs.begin();
            it!=execs.end(); it++) {
        arl::dm::ITypeExecProc *exec = 
            dynamic_cast<arl::dm::ITypeExecProc *>(it->get());
        if (is_b.check(exec->getBody())) {
            TaskGenerateExecModelExecScopeB(
                m_gen, 
                m_refgen, 
                m_out_h,
                m_out_c).generate(exec->getBody());
        }
    }

    OutputStr out(m_out_c->ind());

    m_out_c->println("static zsp_rt_task_t *%s_run(struct %s_s *actor, zsp_rt_task_t *this_p) {",
        fname.c_str(),
        m_gen->getActorName().c_str());
    m_out_c->inc_ind();
    m_out_c->println("zsp_rt_task_t *ret = 0;");

    m_out_c->println("switch(this_p->idx) {");
    m_out_c->inc_ind();
    int32_t start_i = -1;
    for (std::vector<arl::dm::ITypeExecUP>::const_iterator
            it=execs.begin();
            it!=execs.end(); it++) {
        m_out_c->println("case %d: {", idx++);
        m_out_c->inc_ind();
        m_out_c->println("this_p->idx++;");
        arl::dm::ITypeExecProc *exec = 
            dynamic_cast<arl::dm::ITypeExecProc *>(it->get());
        if (is_b.check(exec->getBody())) {
            m_out_c->println("zsp_rt_task_t *task = zsp_rt_task_enter(");
            m_out_c->inc_ind();
            m_out_c->println("&actor->actor,");
            m_out_c->println("sizeof(zsp_rt_task_t),");
            m_out_c->println("0);");
            m_out_c->dec_ind();
            m_out_c->println("task->func = (zsp_rt_task_f)&exec_%p;", exec->getBody());
            m_out_c->println("if ((ret=zsp_rt_task_run(&actor->actor, task))) {");
            m_out_c->println("    break;");
            m_out_c->println("}");
        } else {
            // TaskGenerateExecModelExecScopeNB(m_gen, m_refgen, m_out_c).generate(
            //     exec->getBody(), false);
        }

        m_out_c->dec_ind();
        m_out_c->println("}");
    }

    m_out_c->dec_ind();
    m_out_c->println("}"); // end-switch

    m_out_c->println("return ret;");

    m_out_c->dec_ind();
    m_out_c->println("}");
}

}
}
}
