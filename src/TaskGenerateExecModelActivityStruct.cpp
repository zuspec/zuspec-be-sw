/*
 * TaskGenerateExecModelActivityStruct.cpp
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
#include "TaskGenerateExecModelActivityStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelActivityStruct::TaskGenerateExecModelActivityStruct(
        TaskGenerateExecModel       *gen,
        IOutput                     *out) :
        m_gen(gen), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelActivityStruct", gen->getDebugMgr());
}

TaskGenerateExecModelActivityStruct::~TaskGenerateExecModelActivityStruct() {

}

void TaskGenerateExecModelActivityStruct::generate(vsc::dm::IDataType *activity) {
    DEBUG_ENTER("generate");
    m_struct_t = m_gen->getNameMap()->getName(activity);
    m_out->println("typedef struct %s_s {", m_struct_t.c_str());
    m_out->inc_ind();
    m_out->println("zsp_rt_task_t task;");
    m_depth = 0;
    activity->accept(m_this);
    m_out->dec_ind();
    m_out->println("} %s_t;", m_struct_t.c_str());
    DEBUG_LEAVE("generate");
}

dmgr::IDebug *TaskGenerateExecModelActivityStruct::m_dbg = 0;

}
}
}
