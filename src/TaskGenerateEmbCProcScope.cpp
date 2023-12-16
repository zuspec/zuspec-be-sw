/*
 * TaskGenerateEmbCProcScope.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include <map>
#include "dmgr/impl/DebugMacros.h"
#include "TaskGenerateEmbCVarDecl.h"
#include "TaskGenerateEmbCProcScope.h"

using namespace zsp::arl::dm;
using namespace vsc::dm;


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCProcScope::TaskGenerateEmbCProcScope(
    IContext                    *ctxt,
    IOutput                     *out,
    ITaskGenerateExpr           *expr_gen) : 
        m_ctxt(ctxt), m_out(out), m_expr_gen(expr_gen) {
    DEBUG_INIT("TaskGenerateEmbCProcScope", ctxt->getDebugMgr());

}

TaskGenerateEmbCProcScope::~TaskGenerateEmbCProcScope() {

}

void TaskGenerateEmbCProcScope::generate(
    vsc::dm::IDataTypeStruct    *type_scope,
    arl::dm::ITypeProcStmtScope *scope) {
    m_type_s = type_scope;
    scope->accept(m_this);
}

void TaskGenerateEmbCProcScope::visitTypeProcStmtAssign(ITypeProcStmtAssign *s) {
    std::map<TypeProcStmtAssignOp,std::string> op_m = {
        {TypeProcStmtAssignOp::Eq, "="},
        {TypeProcStmtAssignOp::PlusEq, "+="},
        {TypeProcStmtAssignOp::MinusEq, "-="},
        {TypeProcStmtAssignOp::ShlEq, "<<="},
        {TypeProcStmtAssignOp::ShrEq, ">>="},
        {TypeProcStmtAssignOp::OrEq, "|="},
        {TypeProcStmtAssignOp::AndEq, "&="}
    };
    m_expr_gen->init(m_type_s, &m_scope_s);

    m_out->indent();
    m_expr_gen->generate(m_out, s->getLhs());
    m_out->write(" %s ", op_m.find(s->op())->second.c_str());
    m_expr_gen->generate(m_out, s->getRhs());
    m_out->write(";\n");
}

void TaskGenerateEmbCProcScope::visitTypeProcStmtBreak(ITypeProcStmtBreak *s) {
    m_out->println("break;");
}

void TaskGenerateEmbCProcScope::visitTypeProcStmtContinue(ITypeProcStmtContinue *s) {
    m_out->println("continue;");

}

void TaskGenerateEmbCProcScope::visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) {
    m_out->indent();
    m_expr_gen->init(m_type_s, &m_scope_s);

    m_expr_gen->generate(m_out, s->getExpr());
    m_out->write(";\n");
}

void TaskGenerateEmbCProcScope::visitTypeProcStmtForeach(ITypeProcStmtForeach *s) {

}

void TaskGenerateEmbCProcScope::visitTypeProcStmtIfElse(ITypeProcStmtIfElse *s) {
    m_out->print("if (");
    s->getCond()->accept(m_this);
    m_out->write(") {\n");
    m_out->inc_ind();
    s->getTrue()->accept(m_this);
    m_out->dec_ind();

    if (s->getFalse()) {
        m_out->println("} else {");
        m_out->inc_ind();
        s->getFalse()->accept(m_this);
        m_out->dec_ind();
    }

    m_out->println("}");
}

void TaskGenerateEmbCProcScope::visitTypeProcStmtMatch(ITypeProcStmtMatch *s) {

}

void TaskGenerateEmbCProcScope::visitTypeProcStmtRepeat(ITypeProcStmtRepeat *s) {

}

void TaskGenerateEmbCProcScope::visitTypeProcStmtRepeatWhile(ITypeProcStmtRepeatWhile *s) {

}

void TaskGenerateEmbCProcScope::visitTypeProcStmtReturn(ITypeProcStmtReturn *s) {
    if (s->getExpr()) {
        m_expr_gen->init(m_type_s, &m_scope_s);

        m_out->print("return ");
        m_expr_gen->generate(m_out, s->getExpr());
        m_out->write(";\n");
    } else {
        m_out->println("return;");
    }
}

void TaskGenerateEmbCProcScope::visitTypeProcStmtScope(ITypeProcStmtScope *s) {
    if (m_scope_s.size() > 1) {
        m_out->println("{");
        m_out->inc_ind();
    }

    // Generate all in-scope declarations at the beginning of the scope
    TaskGenerateEmbCVarDecl decl_gen(m_ctxt, m_out);
    for (std::vector<ITypeProcStmtUP>::const_iterator
        it=s->getStatements().begin();
        it!=s->getStatements().end(); it++) {
        decl_gen.generate(it->get());
    }

    m_scope_s.push_back(s);
    for (std::vector<ITypeProcStmtUP>::const_iterator
        it=s->getStatements().begin();
        it!=s->getStatements().end(); it++) {
        (*it)->accept(m_this);
    }
    m_scope_s.pop_back();

    if (m_scope_s.size() > 1) {
        m_out->dec_ind();
        m_out->println("}");
    }

}

void TaskGenerateEmbCProcScope::visitTypeProcStmtVarDecl(ITypeProcStmtVarDecl *s) {
    // Ignore here. Handled by the containing scope
}

void TaskGenerateEmbCProcScope::visitTypeProcStmtWhile(ITypeProcStmtWhile *s) {

}

dmgr::IDebug *TaskGenerateEmbCProcScope::m_dbg = 0;

}
}
}
