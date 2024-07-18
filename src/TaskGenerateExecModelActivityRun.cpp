/*
 * TaskGenerateExecModelActivityRun.cpp
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
#include "zsp/arl/dm/impl/TaskActionHasMemClaim.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelActivityRun.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelActivityRun::TaskGenerateExecModelActivityRun(
    TaskGenerateExecModel       *gen,
    IOutput                     *out) : m_gen(gen), m_out(out) {
    DEBUG_INIT("zsp::be::Sw::TaskGenerateExecModelActivityRun", gen->getDebugMgr());
}

TaskGenerateExecModelActivityRun::~TaskGenerateExecModelActivityRun() {

}

void TaskGenerateExecModelActivityRun::generate(
    vsc::dm::IDataType *activity) {
    DEBUG_ENTER("generate");
    m_idx = 0;
    m_depth = 0;
    m_out->println("zsp_rt_task_t *%s_run(struct %s_s *actor, struct %s_s *this_p) {",
        m_gen->getNameMap()->getName(activity).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(activity).c_str());
    m_out->inc_ind();
    m_out->println("zsp_rt_task_t *ret = 0;");

    m_out->println("");
    m_out->println("switch (this_p->task.idx) {");
    m_out->inc_ind();
    m_out->println("case %d: {", m_idx++);
    m_out->inc_ind();
    m_out->println("this_p->task.idx++;");

    activity->accept(m_this);

    // Close out whichever scope is still open
    m_out->dec_ind();
    m_out->println("}");
    m_out->dec_ind();
    m_out->println("}");
    m_out->println("return ret;");
    m_out->dec_ind();
    m_out->println("}");
    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelActivityRun::visitDataTypeActivitySequence(arl::dm::IDataTypeActivitySequence *t) { 
    DEBUG_ENTER("visitDataTypeActivitySequence");
    if (m_depth == 0) {
        // We can treat this scope as being part of the root
        for (std::vector<arl::dm::ITypeFieldActivityUP>::const_iterator
            it=t->getActivities().begin();
            it!=t->getActivities().end(); it++) {
            (*it)->getDataType()->accept(m_this);
        }
    } else {
        // We need to create a new activity and call it
    }

    DEBUG_LEAVE("visitDataTypeActivitySequence");
}

void TaskGenerateExecModelActivityRun::visitDataTypeActivityTraverse(arl::dm::IDataTypeActivityTraverse *t) { 
    DEBUG_ENTER("visitDataTypeActivityTraverse");
    m_out->println("struct %s_s *h_%p = (struct %s_s)zsp_rt_task_enter(",
        m_gen->getNameMap()->getName(t).c_str(),
        t,
        m_gen->getNameMap()->getName(t).c_str());
    m_out->inc_ind();
    m_out->println("&actor->actor,");
    m_out->println("sizeof(%s_t),",
        m_gen->getNameMap()->getName(t).c_str());
    m_out->println("(zsp_rt_init_f)&%s_init);",
        m_gen->getNameMap()->getName(t).c_str());
    m_out->dec_ind();
    m_out->println("");

    m_out->println("if ((ret=zsp_rt_task_run(&actor->actor, &h_%p->task))) {");
    m_out->inc_ind();
    m_out->println("break;");
    m_out->dec_ind();
    m_out->println("}");

    // Close out the block that we were in
    m_out->dec_ind();
    m_out->println("}");

    // Open a new one
    m_out->println("case %d: {", m_idx++);
    m_out->inc_ind();

    // Clean up after the traversed action
    m_out->println("// TODO: call dtor");

    DEBUG_LEAVE("visitDataTypeActivityTraverse");
}

void TaskGenerateExecModelActivityRun::visitDataTypeActivityTraverseType(arl::dm::IDataTypeActivityTraverseType *t) { 
    DEBUG_ENTER("visitDataTypeActivityTraverseType");
    m_out->println("struct %s_s *h_%p = (struct %s_s *)zsp_rt_task_enter(",
        m_gen->getNameMap()->getName(t->getTarget()).c_str(),
        t,
        m_gen->getNameMap()->getName(t->getTarget()).c_str());
    m_out->inc_ind();
    m_out->println("&actor->actor,");
    m_out->println("sizeof(%s_t),",
        m_gen->getNameMap()->getName(t->getTarget()).c_str());
    m_out->println("(zsp_rt_init_f)&%s__init);",
        m_gen->getNameMap()->getName(t->getTarget()).c_str());
    m_out->dec_ind();
    m_out->println("");

    m_out->println("if ((ret=zsp_rt_task_run(&actor->actor, &h_%p->task))) {", t);
    m_out->inc_ind();
    m_out->println("break;");
    m_out->dec_ind();
    m_out->println("}");

    // Close out the block that we were in
    m_out->dec_ind();
    m_out->println("}");

    // Open a new one
    m_out->println("case %d: {", m_idx++);
    m_out->inc_ind();
    DEBUG_LEAVE("visitDataTypeActivityTraverseType");
}

dmgr::IDebug *TaskGenerateExecModelActivityRun::m_dbg = 0;

}
}
}
