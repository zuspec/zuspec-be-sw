/*
 * TaskBuildAsyncScopeGroup.cpp
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
#include "TaskBuildAsyncScopeGroup.h"


namespace zsp {
namespace be {
namespace sw {


TaskBuildAsyncScopeGroup::TaskBuildAsyncScopeGroup(IContext *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("zsp.be.sw.TaskBuildAsyncScopeGroup", ctxt->getDebugMgr());
}

TaskBuildAsyncScopeGroup::~TaskBuildAsyncScopeGroup() {

}

TypeProcStmtAsyncScopeGroup *TaskBuildAsyncScopeGroup::build(
    const std::vector<arl::dm::ITypeExecUP> &execs) {
    DEBUG_ENTER("build");
    m_scopes.push_back(TypeProcStmtAsyncScopeUP(new TypeProcStmtAsyncScope(0)));

    // Default case
    m_scopes.push_back(TypeProcStmtAsyncScopeUP(new TypeProcStmtAsyncScope(-1)));

    for (std::vector<arl::dm::ITypeExecUP>::const_iterator
        it=execs.begin();
        it!=execs.end(); it++) {
        (*it)->accept(this);
    }

    if (m_scopes.size() > 2) {
        // An actual async scope was created

        if (m_scopes.at(m_scopes.size()-2)->getStatements().size() == 0) {
            // Remove the last actual scope since it has no statements
            m_scopes.erase(m_scopes.end()-2);
        }
    }


    DEBUG_LEAVE("build");
    return 0;
}

TypeProcStmtAsyncScopeGroup *TaskBuildAsyncScopeGroup::build(vsc::dm::IAccept *scope) {
    DEBUG_ENTER("build");    
    m_scopes.push_back(TypeProcStmtAsyncScopeUP(new TypeProcStmtAsyncScope(0)));

    // Default case
    m_scopes.push_back(TypeProcStmtAsyncScopeUP(new TypeProcStmtAsyncScope(-1)));

    scope->accept(this);

    if (m_scopes.size() > 2) {
        // An actual async scope was created

        if (m_scopes.at(m_scopes.size()-2)->getStatements().size() == 0) {
            // Remove the last actual scope since it has no statements
            m_scopes.erase(m_scopes.end()-2);
        }
    }

    
    DEBUG_LEAVE("build %d", m_scopes.size());
    return 0;
}

void TaskBuildAsyncScopeGroup::visitDataTypeAction(arl::dm::IDataTypeAction *t) {
    DEBUG_ENTER("visitDataTypeAction");
    if (t->activities().size() > 0) {
        if (t->activities().size() > 1) {
            // TODO: Create a schedule 
            DEBUG("Action %s has %d activities", t->name().c_str(), t->activities().size());
        } else {
            DEBUG("Action %s has 1 activity", t->name().c_str());
        }
    } else {
        DEBUG("No activities in action %s", t->name().c_str());
    }
    DEBUG_LEAVE("visitDataTypeAction");
}

void TaskBuildAsyncScopeGroup::visitDataTypeActivity(arl::dm::IDataTypeActivity *t) {
    DEBUG_ENTER("visitDataTypeActivity");
    DEBUG_LEAVE("visitDataTypeActivity");
}

void TaskBuildAsyncScopeGroup::visitTypeExprBin(vsc::dm::ITypeExprBin *e) {
    vsc::dm::ITypeExprUP lhs, rhs;
    m_expr.reset();
    e->lhs()->accept(this);
    lhs = std::move(m_expr);
    m_expr.reset();
    e->rhs()->accept(this);
    rhs = std::move(m_expr);

    if (lhs || rhs) {
        m_expr = vsc::dm::ITypeExprUP(m_ctxt->ctxt()->mkTypeExprBin(
            (lhs)?lhs.get():e->lhs(),
            e->op(),
            (rhs)?rhs.get():e->rhs(),
            lhs.get(),
            rhs.get()
        ));
        lhs.release();
        rhs.release();
    }
}

void TaskBuildAsyncScopeGroup::visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) {
    DEBUG_ENTER("visitTypeExprMethodCallContext");
    TypeProcStmtAsyncScope *scope = currentScope();
    std::vector<vsc::dm::ITypeExprUP> blocking_params;

    // First, visit all parameter expressions 
    for (std::vector<vsc::dm::ITypeExprUP>::const_iterator 
        it=e->getParameters().begin();
        it!=e->getParameters().end(); it++) {
        m_expr.reset();
        (*it)->accept(m_this);
        blocking_params.push_back(std::move(m_expr));
    }

    if (currentScope() != scope) {
        DEBUG("New scope created while evaluating parameters");
        // We need to rewrite the method call, since some of the
        // parameter expressions were blocking

        // TODO: Release any temp variables
    }

    // TODO: if the method itself is blocking, then we need to
    // introduce a new scope with a temp assignment on the other
    // side to retrieve the method result

    DEBUG_LEAVE("visitTypeExprMethodCallContext");
}

void TaskBuildAsyncScopeGroup::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) {
    DEBUG_ENTER("visitTypeExprMethodCallStatic");
//    if (m_imp_target_blocking && e->getTarget()->hasFlags(arl::dm::DataTypeFunctionFlags::Import)) {

    DEBUG_LEAVE("visitTypeExprMethodCallStatic");
}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) { 

}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtRepeatWhile(arl::dm::ITypeProcStmtRepeatWhile *s) { 

}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtWhile(arl::dm::ITypeProcStmtWhile *s) { 

}

void TaskBuildAsyncScopeGroup::visitTypeProcStmtYield(arl::dm::ITypeProcStmtYield *s) { 
    DEBUG_ENTER("visitTypeProcStmtYield");
    // This statement belongs in the current scope
    // Need to introduce a new scope for subsequent statements
    m_scopes.at(m_scopes.size()-2)->addStatement(s, false);

    m_scopes.insert(
        m_scopes.end()-1,
        TypeProcStmtAsyncScopeUP(new TypeProcStmtAsyncScope(m_scopes.size()-1)));
    
    DEBUG_LEAVE("visitTypeProcStmtYield");
}

dmgr::IDebug *TaskBuildAsyncScopeGroup::m_dbg = 0;

}
}
}
