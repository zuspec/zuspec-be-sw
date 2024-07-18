/*
 * TaskGenerateExecModelAddrClaimStruct.cpp
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
#include "TaskGenerateExecModelAddrClaimStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelAddrClaimStruct::TaskGenerateExecModelAddrClaimStruct(
    TaskGenerateExecModel       *gen,
    IOutput                     *out) : TaskGenerateExecModelStructStruct(gen, out) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelAddrClaimStruct", gen->getDebugMgr());
}

TaskGenerateExecModelAddrClaimStruct::~TaskGenerateExecModelAddrClaimStruct() {

}

void TaskGenerateExecModelAddrClaimStruct::generate_prefix(vsc::dm::IDataTypeStruct *i) {
    TaskGenerateExecModelStructStruct::generate_prefix(i);
    m_out->println("zsp_rt_addr_claim_t *claim;");
}

void TaskGenerateExecModelAddrClaimStruct::generate_dtor(vsc::dm::IDataTypeStruct *i) {
    m_out->println("void %s__dtor(%s_t *actor, %s_t *this_p) {",
        m_gen->getNameMap()->getName(i).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(i).c_str());
    m_out->inc_ind();
    m_out->println("zsp_rt_rc_dec(this_p->claim);");
    m_out->dec_ind();
    m_out->println("}");
}

}
}
}
