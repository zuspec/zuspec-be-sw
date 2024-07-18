/*
 * TaskGenerateExecModelCompStruct.cpp
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
#include "TaskGenerateExecModelCompStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelCompStruct::TaskGenerateExecModelCompStruct(
    TaskGenerateExecModel       *gen,
    IOutput                     *out) : 
        TaskGenerateExecModelStructStruct(gen, out) {

}

TaskGenerateExecModelCompStruct::~TaskGenerateExecModelCompStruct() {

}

void TaskGenerateExecModelCompStruct::generate_prefix(vsc::dm::IDataTypeStruct *i) {
    m_out->println("typedef struct %s_s {", m_gen->getNameMap()->getName(i).c_str());
    m_out->inc_ind();
    m_out->println("zsp_rt_component_t comp;");
    m_out->println("zsp_rt_aspace_idx_t __aspace[%d];", m_gen->getNumTraitTypes());
}

void TaskGenerateExecModelCompStruct::visitDataTypeAddrSpaceTransparentC(arl::dm::IDataTypeAddrSpaceTransparentC *t) {
    m_out->write("%s_t ", m_gen->getNameMap()->getName(t).c_str());
}

}
}
}
