/*
 * TaskGenerateExecModelActivity.cpp
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
#include "TaskGenerateExecModelActivity.h"
#include "TaskGenerateExecModelActivityInit.h"
#include "TaskGenerateExecModelActivityRun.h"
#include "TaskGenerateExecModelActivityStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelActivity::TaskGenerateExecModelActivity(
    TaskGenerateExecModel       *gen) : m_gen(gen) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelActivity",
        gen->getDebugMgr());
}

TaskGenerateExecModelActivity::~TaskGenerateExecModelActivity() {

}

void TaskGenerateExecModelActivity::generate(vsc::dm::IDataType *activity) {
    DEBUG_ENTER("generate");
    TaskGenerateExecModelActivityStruct(
        m_gen,
        m_gen->getOutHPrv()).generate(activity);

    TaskGenerateExecModelActivityInit(
        m_gen,
        m_gen->getOutC()).generate(activity);

    TaskGenerateExecModelActivityRun(
        m_gen,
        m_gen->getOutC()).generate(activity);

    DEBUG_LEAVE("generate");
}

dmgr::IDebug *TaskGenerateExecModelActivity::m_dbg = 0;

}
}
}
