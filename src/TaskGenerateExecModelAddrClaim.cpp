/*
 * TaskGenerateExecModelAddrClaim.cpp
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
#include "TaskGenerateExecModelAddrClaim.h"
#include "TaskGenerateExecModelAddrClaimStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelAddrClaim::TaskGenerateExecModelAddrClaim(
        TaskGenerateExecModel       *gen,
        IOutput                     *out_h,
        IOutput                     *out_c) : TaskGenerateExecModelStruct(gen, out_h, out_c) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelAddrClaim", gen->getDebugMgr());
}

TaskGenerateExecModelAddrClaim::~TaskGenerateExecModelAddrClaim() {

}

void TaskGenerateExecModelAddrClaim::generate_type(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("generate");
    TaskGenerateExecModelAddrClaimStruct(m_gen, m_out_h).generate(t);
    DEBUG_LEAVE("generate");
}



}
}
}
