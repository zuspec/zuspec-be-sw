/*
 * TaskGenerateExecModelCountBlockingScopes.cpp
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
#include "TaskGenerateExecModelCountBlockingScopes.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelCountBlockingScopes::TaskGenerateExecModelCountBlockingScopes(
    TaskGenerateExecModel   *gen) : m_gen(gen) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelCountBlockingScopes", gen->getDebugMgr());
}

TaskGenerateExecModelCountBlockingScopes::~TaskGenerateExecModelCountBlockingScopes() {

}

int32_t TaskGenerateExecModelCountBlockingScopes::count(arl::dm::IDataTypeActivity *t) {
    DEBUG_ENTER("count");
    m_count = 0;
    t->accept(m_this);
    DEBUG_LEAVE("count %d", m_count);
    return m_count;
}

void TaskGenerateExecModelCountBlockingScopes::visitDataTypeActivityParallel(
    arl::dm::IDataTypeActivityParallel *t) { 
    m_count++;
}

void TaskGenerateExecModelCountBlockingScopes::visitDataTypeActivityReplicate(
    arl::dm::IDataTypeActivityReplicate *t) { 
    m_count++;
}

void TaskGenerateExecModelCountBlockingScopes::visitDataTypeActivitySequence(
    arl::dm::IDataTypeActivitySequence *t) { 
    m_count++;
}

void TaskGenerateExecModelCountBlockingScopes::visitDataTypeActivityTraverse(
    arl::dm::IDataTypeActivityTraverse *t) { 
    m_count++;
}

dmgr::IDebug *TaskGenerateExecModelCountBlockingScopes::m_dbg = 0;

}
}
}
