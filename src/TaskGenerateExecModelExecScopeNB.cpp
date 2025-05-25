/*
 * TaskGenerateExecModelExecScopeNB.cpp
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
#include "GenRefExprExecModel.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExecVarInit.h"
#include "TaskGenerateExecModelExecScopeNB.h"
#include "TaskGenerateExprNB.h"
#include "TaskGenerateExecModelVarType.h"
#include "TaskGenerateExecModelUpdateRCField.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelExecScopeNB::TaskGenerateExecModelExecScopeNB(
    TaskGenerateExecModel   *gen,
    IGenRefExpr             *refgen,
    IOutput                 *out) : 
    m_dbg(0), m_gen(gen), m_refgen(refgen), m_out(out),
    m_var(0), m_expr(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelExecScopeNB", gen->getDebugMgr());
}

TaskGenerateExecModelExecScopeNB::~TaskGenerateExecModelExecScopeNB() {

}

void TaskGenerateExecModelExecScopeNB::generate(
        arl::dm::ITypeExec                      *i,
        bool                                    new_scope) {
    m_out_s.push_back(OutputExecScope(new_scope, m_out));
    i->accept(m_this);
    m_out_s.back().apply(m_out);
}

void TaskGenerateExecModelExecScopeNB::generate(
        arl::dm::ITypeProcStmt                  *i,
        bool                                    new_scope) {
    m_out_s.push_back(OutputExecScope(new_scope, m_out));
    i->accept(m_this);
    m_out_s.back().apply(m_out);
}

void TaskGenerateExecModelExecScopeNB::generate(
        const std::vector<arl::dm::ITypeExecUP> &i,
        bool                                    new_scope) {

    for (std::vector<arl::dm::ITypeExecUP>::const_iterator
        it=i.begin();
        it!=i.end(); it++) {
        m_out_s.push_back(OutputExecScope(new_scope, m_gen->getOutC()));
        (*it)->accept(m_this);
        m_out_s.back().apply(m_gen->getOutC());
        new_scope |= (i.size() > 1);
    }
}

void TaskGenerateExecModelExecScopeNB::visitTypeProcStmtAssign(arl::dm::ITypeProcStmtAssign *s) {
    DEBUG_ENTER("visitTypeProcStmtAssign");
    // if is a ref-counted field, dec ref of previous value
    IGenRefExpr::ResT is_rc = m_refgen->isRefCountedField(s->getLhs());

    if (is_rc.first) {
        TaskGenerateExecModelUpdateRCField(m_refgen).generate_release(
            m_out_s.back().exec(),
            is_rc.second,
            s->getLhs());
    }

    m_out_s.back().exec()->indent();
    m_out_s.back().exec()->write("%s = ",
        m_refgen->genLval(s->getLhs()).c_str());
    TaskGenerateExprNB(
        m_gen, 
        m_refgen, 
        m_out_s.back().exec()).generate(s->getRhs());
    m_out_s.back().exec()->write(";\n");

    // if is a ref-counted field, inc ref of new value
    if (is_rc.first) {
        TaskGenerateExecModelUpdateRCField(m_refgen).generate_acquire(
            m_out_s.back().exec(),
            is_rc.second,
            s->getLhs());
    }
    DEBUG_LEAVE("visitTypeProcStmtAssign");
}

void TaskGenerateExecModelExecScopeNB::visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) {
    DEBUG_ENTER("visitTypeProcStmtExpr");
    m_out_s.back().exec()->indent();
    TaskGenerateExprNB(
        m_gen, 
        m_refgen, 
        m_out_s.back().exec()).generate(s->getExpr());
    m_out_s.back().exec()->write(";\n");
    DEBUG_LEAVE("visitTypeProcStmtExpr");
}

void TaskGenerateExecModelExecScopeNB::visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) {
    DEBUG_ENTER("visitTypeScopeStmtScope");
    m_refgen->pushScope(s);
    arl::dm::VisitorBase::visitTypeProcStmtScope(s);
    m_refgen->popScope();
    DEBUG_LEAVE("visitTypeScopeStmtScope");
}

void TaskGenerateExecModelExecScopeNB::visitTypeProcStmtIfClause(arl::dm::ITypeProcStmtIfClause *s) {
    DEBUG_ENTER("visitTypeProcStmtIfClause");
    DEBUG_LEAVE("visitTypeProcStmtIfClause");
}

void TaskGenerateExecModelExecScopeNB::visitTypeProcStmtIfElse(arl::dm::ITypeProcStmtIfElse *s) {
    DEBUG_ENTER("visitTypeProcStmtIfElse");
    for (std::vector<arl::dm::ITypeProcStmtIfClauseUP>::const_iterator
        it=s->getIfClauses().begin();
        it!=s->getIfClauses().end(); it++) {
        m_out_s.back().exec()->indent();
        if (it != s->getIfClauses().begin()) {
            m_out_s.back().exec()->write("} else ");
        }

        m_out_s.back().exec()->write("if (");
        TaskGenerateExprNB(
            m_gen, 
            m_refgen, 
            m_out_s.back().exec()).generate((*it)->getCond());
        m_out_s.back().exec()->write(") {\n");
        m_out_s.back().exec()->inc_ind();
        TaskGenerateExecModelExecScopeNB(
            m_gen, 
            m_refgen, 
            m_out_s.back().exec()).generate(
            (*it)->getStmt(),
            false
        );
        m_out_s.back().exec()->dec_ind();
    }

    if (s->getElseClause()) {
        m_out_s.back().exec()->println("} else {");
        m_out_s.back().exec()->inc_ind();
        TaskGenerateExecModelExecScopeNB(
            m_gen, 
            m_refgen, 
            m_out_s.back().exec()).generate(
            s->getElseClause(),
            false
        );
        m_out_s.back().exec()->dec_ind();
    }
    m_out_s.back().exec()->println("}");
    DEBUG_LEAVE("visitTypeProcStmtIfElse");
}

void TaskGenerateExecModelExecScopeNB::visitTypeProcStmtVarDecl(arl::dm::ITypeProcStmtVarDecl *s) {
    DEBUG_ENTER("visitTypeProcStmtVarDecl %s", s->name().c_str());
    IGenRefExpr::ResT is_rc = m_refgen->isRefCountedField(s->getDataType());

    m_out_s.back().decl()->indent();
    TaskGenerateExecModelVarType(
        m_gen, 
        m_out_s.back().decl(),
        false).generate(s->getDataType());
    m_out_s.back().decl()->write("%s", s->name().c_str());
    if (s->getInit()) {
        m_out_s.back().decl()->write(" = "); 
        TaskGenerateExprNB(
            m_gen, 
            m_refgen, 
            m_out_s.back().decl()).generate(s->getInit());
        if (is_rc.first) {
            TaskGenerateExecModelUpdateRCField(m_refgen).generate_acquire(
                m_out_s.back().init(),
                s);
        }
    } else {
        // generate default initial value
        TaskGenerateExecModelExecVarInit(
            m_gen,
            m_out_s.back().init()).generate(s);
    }

    if (is_rc.first) {
        TaskGenerateExecModelUpdateRCField(m_refgen).generate_release(
            m_out_s.back().dtor(),
            s);
    }

    m_out_s.back().decl()->write(";\n"); 
    DEBUG_LEAVE("visitTypeProcStmtVarDecl");
}

void TaskGenerateExecModelExecScopeNB::visitDataTypeAddrClaim(arl::dm::IDataTypeAddrClaim *t) {
    DEBUG_ENTER("visitDataTypeAddrClaim");

    DEBUG_LEAVE("visitDataTypeAddrClaim");
}

void TaskGenerateExecModelExecScopeNB::visitDataTypeAddrHandle(arl::dm::IDataTypeAddrHandle *t) {
    DEBUG_ENTER("visitDataTypeAddrHandle");
    m_out_s.back().exec()->println("zsp_rt_rc_inc(%s.store);",
        m_var->name().c_str());
    m_out_s.back().dtor()->println("zsp_rt_rc_dec(%s.store);",
        m_var->name().c_str());
    DEBUG_LEAVE("visitDataTypeAddrHandle");
}

}
}
}
