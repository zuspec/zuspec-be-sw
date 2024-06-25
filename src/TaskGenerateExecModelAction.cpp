/*
 * TaskGenerateExecModelAction.cpp
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
#include "TaskGenerateExecModelAction.h"
#include "TaskGenerateExecModelActionStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelAction::TaskGenerateExecModelAction(
    TaskGenerateExecModel   *gen,
    bool                    is_root) : m_gen(gen), m_is_root(is_root), m_depth(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelAction", gen->getDebugMgr());
}

TaskGenerateExecModelAction::~TaskGenerateExecModelAction() {

}

void TaskGenerateExecModelAction::generate(arl::dm::IDataTypeAction *action) {

    // Declare the action struct
    TaskGenerateExecModelActionStruct(m_gen, m_gen->getOutHPrv()).generate(action);

    // Declare the action-init function
    m_gen->getOutC()->println("void %s__init(struct %s_s *actor, struct %s_s *this_p) {",
        m_gen->getNameMap()->getName(action).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(action).c_str());
    m_gen->getOutC()->inc_ind();
    m_gen->getOutC()->println("this_p->task.func = (zsp_rt_task_f)&%s__run;",
        m_gen->getNameMap()->getName(action).c_str());
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");

    // Now, declare the action-run function
    m_gen->getOutC()->println("zsp_rt_task_t *%s__run(struct %s_s *actor, struct %s_s *this_p) {",
        m_gen->getNameMap()->getName(action).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(action).c_str());
    m_gen->getOutC()->println("zsp_rt_task_t *ret = 0;");
    m_gen->getOutC()->inc_ind();
    m_gen->getOutC()->println("switch (this_p->task.idx) {");
    m_gen->getOutC()->inc_ind();
    m_gen->getOutC()->println("case 0: {");
    m_gen->getOutC()->inc_ind();
    m_gen->getOutC()->println("fprintf(stdout, \"Hello from action run\\n\");");
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");
    m_gen->getOutC()->println("return ret;");
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");

    // Forward declaration
    /*
    TaskGenerateFwdDecl(
        m_gen->getDebugMgr(),
        m_gen->getNameMap(),
        m_gen->getOutHPrv()).generate(action);
     */

    // 

}

void TaskGenerateExecModelAction::visitDataTypeAction(arl::dm::IDataTypeAction *i) {
    DEBUG_ENTER("visitDataTypeAction");
    if (m_depth == 0) {
        m_depth++;

        // Recurse first to find any sub-types that may 
        // need to be created first
        VisitorBase::visitDataTypeAction(i);

        // Now, declare the type and implement the methods

        m_depth--;
    } else if (!m_gen->fwdDecl(i)) {
        // 
        TaskGenerateExecModelAction(m_gen).generate(i);
    }

    DEBUG_LEAVE("visitDataTypeAction");
}

dmgr::IDebug *TaskGenerateExecModelAction::m_dbg = 0;

}
}
}
