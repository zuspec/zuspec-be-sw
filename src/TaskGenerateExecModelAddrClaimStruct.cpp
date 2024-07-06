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
    IOutput                     *out) : TaskGenerateExecModelStruct(gen, out) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelAddrClaimStruct", gen->getDebugMgr());
}

TaskGenerateExecModelAddrClaimStruct::~TaskGenerateExecModelAddrClaimStruct() {

}

void TaskGenerateExecModelAddrClaimStruct::generate_prefix(vsc::dm::IDataTypeStruct *i) {
    TaskGenerateExecModelStruct::generate_prefix(i);
    m_out->println("zsp_rt_addr_claim_t *claim;");
}

}
}
}
