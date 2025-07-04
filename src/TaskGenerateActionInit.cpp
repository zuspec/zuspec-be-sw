/*
 * TaskGenerateActionInit.cpp
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
#include "TaskGenerateActionInit.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateActionInit::TaskGenerateActionInit(
    IContext                     *ctxt,
    IOutput                      *out_h,
    IOutput                      *out_c) : 
        TaskGenerateStructInit(ctxt, out_h, out_c) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateActionInit", ctxt->getDebugMgr());

}

TaskGenerateActionInit::~TaskGenerateActionInit() {

}

void TaskGenerateActionInit::generate_core(vsc::dm::IDataTypeStruct *i) {
    TaskGenerateStructInit::generate_core(i);
    // m_gen->getOutC()->println("this_p->task.func = (zsp_rt_task_f)&%s__run;",
    //     m_gen->getNameMap()->getName(i).c_str());

}

}
}
}
