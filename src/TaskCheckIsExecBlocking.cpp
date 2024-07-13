/*
 * TaskCheckIsExecBlocking.cpp
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
#include "TaskCheckIsExecBlocking.h"


namespace zsp {
namespace be {
namespace sw {


TaskCheckIsExecBlocking::TaskCheckIsExecBlocking(
    dmgr::IDebugMgr         *dmgr,
    bool                    imp_target_blocking) : 
        m_dmgr(dmgr), m_imp_target_blocking(imp_target_blocking) {
    DEBUG_INIT("zsp::be::sw::TaskCheckIsExecBlocking", dmgr);
}

TaskCheckIsExecBlocking::~TaskCheckIsExecBlocking() {

}

bool TaskCheckIsExecBlocking::check(arl::dm::ITypeExec *exec) {
    DEBUG_ENTER("check");
    m_blocking = false;
    exec->accept(m_this);
    DEBUG_LEAVE("check %d", m_blocking);
    return m_blocking;
}

bool TaskCheckIsExecBlocking::check(arl::dm::ITypeProcStmt *exec) {
    DEBUG_ENTER("check");
    m_blocking = false;
    exec->accept(m_this);
    DEBUG_LEAVE("check %d", m_blocking);
    return m_blocking;
}

bool TaskCheckIsExecBlocking::check(const std::vector<arl::dm::ITypeExecUP> &execs) {
    DEBUG_ENTER("check");
    m_blocking = false;
    for (std::vector<arl::dm::ITypeExecUP>::const_iterator
        it=execs.begin();
        it!=execs.end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("check %d", m_blocking);
    return m_blocking;
}

void TaskCheckIsExecBlocking::visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) {
    if (m_imp_target_blocking && e->getTarget()->hasFlags(arl::dm::DataTypeFunctionFlags::Import)) {
        m_blocking = true;
    } else {
        if (!m_blocking) {
            e->getContext()->accept(m_this);
        } 

        // First, check the parameter expressions
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator 
            it=e->getParameters().begin();
            it!=e->getParameters().end() && !m_blocking; it++) {
            (*it)->accept(m_this);
        }

        if (!m_blocking) {
            e->getTarget()->getBody()->accept(m_this);
        }
    }
}

void TaskCheckIsExecBlocking::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) {
    DEBUG("m_imp_target_blocking: %d", m_imp_target_blocking);
    DEBUG("flags: 0x%08x", e->getTarget()->getFlags());
    if (m_imp_target_blocking && e->getTarget()->hasFlags(arl::dm::DataTypeFunctionFlags::Import)) {
        m_blocking = true;
    } else {
        // First, check the parameter expressions
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator 
            it=e->getParameters().begin();
            it!=e->getParameters().end() && !m_blocking; it++) {
            (*it)->accept(m_this);
        }

        if (!m_blocking) {
            e->getTarget()->getBody()->accept(m_this);
        }
    }
}

void TaskCheckIsExecBlocking::visitTypeProcStmtYield(arl::dm::ITypeProcStmtYield *t) {
    m_blocking = true;
}

dmgr::IDebug *TaskCheckIsExecBlocking::m_dbg = 0;

}
}
}
