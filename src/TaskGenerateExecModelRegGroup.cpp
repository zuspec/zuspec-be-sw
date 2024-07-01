/*
 * TaskGenerateExecModelRegGroup.cpp
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
#include "TaskGenerateExecModelRegGroup.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelRegGroup::TaskGenerateExecModelRegGroup(
    TaskGenerateExecModel           *gen,
    IOutput                         *out_h,
    IOutput                         *out_c) : TaskGenerateExecModelStruct(gen, out_h) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelRegGroup", gen->getDebugMgr());
}

TaskGenerateExecModelRegGroup::~TaskGenerateExecModelRegGroup() {

}

void TaskGenerateExecModelRegGroup::generate(vsc::dm::IDataType *t) {
    DEBUG_ENTER("generate");
    m_out->println("typedef struct %s_s {", m_gen->getNameMap()->getName(t).c_str());
    m_out->inc_ind();
    m_depth = 0;
    m_ptr = 0;
    m_field = 0;
    m_field_m.clear();
    t->accept(m_this);
    m_out->dec_ind();
    m_out->println("} %s_t;", m_gen->getNameMap()->getName(t).c_str());
    DEBUG_LEAVE("generate");
}

}
}
}
