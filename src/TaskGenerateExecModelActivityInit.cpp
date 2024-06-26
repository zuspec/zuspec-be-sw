/*
 * TaskGenerateExecModelActivityInit.cpp
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
#include "TaskGenerateExecModelActivityInit.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelActivityInit::TaskGenerateExecModelActivityInit(
    TaskGenerateExecModel       *gen,
    IOutput                     *out) : m_gen(gen), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelActivityInit", gen->getDebugMgr());        
}

TaskGenerateExecModelActivityInit::~TaskGenerateExecModelActivityInit() {

}

void TaskGenerateExecModelActivityInit::generate(vsc::dm::IDataType *activity) {
    DEBUG_ENTER("generate");
    m_out->println("void %s_init(struct %s_s *actor, struct %s_s *this_p) {",
        m_gen->getNameMap()->getName(activity).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(activity).c_str());
    m_out->inc_ind();
    m_out->println("this_p->task.func = (zsp_rt_task_f)&%s_run;",
        m_gen->getNameMap()->getName(activity).c_str());
    activity->accept(m_this);
    m_out->dec_ind();
    m_out->println("}");

    DEBUG_LEAVE("generate");
}

dmgr::IDebug *TaskGenerateExecModelActivityInit::m_dbg = 0;

}
}
}
