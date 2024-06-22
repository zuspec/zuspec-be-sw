/*
 * TaskGenerateExecModelAction.cpp
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
#include "TaskGenerateExecModelAction.h"
#include "TaskGenerateExecModelActionStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelAction::TaskGenerateExecModelAction(
    TaskGenerateExecModel   *gen,
    bool                    is_root) : m_gen(gen), m_is_root(is_root), m_depth(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelAction", gen->getDebugMgr());
}

TaskGenerateExecModelAction::~TaskGenerateExecModelAction() {

}

void TaskGenerateExecModelAction::generate(arl::dm::IDataTypeAction *action) {

    // Visit the tree of actions to pre-declare all types
    // Use a depth-first traversal
    action->accept(m_this);

    // Forward declaration
    /*
    TaskGenerateFwdDecl(
        m_gen->getDebugMgr(),
        m_gen->getNameMap(),
        m_gen->getOutHPrv()).generate(action);
     */

    // 

}

void TaskGenerateExecModelAction::visitDataTypeAction(arl::dm::IDataTypeAction *i) {
    DEBUG_ENTER("visitDataTypeAction");
    if (m_depth == 0) {
        m_depth++;

        // Recurse first to find any sub-types that may 
        // need to be created first
        VisitorBase::visitDataTypeAction(i);

        // Now, declare the type and implement the methods
        TaskGenerateExecModelActionStruct(m_gen, m_gen->getOutHPrv()).generate(i);

        m_depth--;
    } else if (!m_gen->fwdDecl(i)) {
        // 
        TaskGenerateExecModelAction(m_gen).generate(i);
    }

    DEBUG_LEAVE("visitDataTypeAction");
}

dmgr::IDebug *TaskGenerateExecModelAction::m_dbg = 0;

}
}
}
