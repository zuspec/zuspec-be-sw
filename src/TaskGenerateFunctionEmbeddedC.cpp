/*
 * TaskGenerateFunctionEmbeddedC.cpp
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
#include "TaskGenerateEmbCExpr.h"
#include "TaskGenerateEmbCVarDecl.h"
#include "TaskGenerateFunctionEmbeddedC.h"

using namespace zsp::arl::dm;

namespace zsp {
namespace be {
namespace sw {


TaskGenerateFunctionEmbeddedC::TaskGenerateFunctionEmbeddedC(NameMap *name_m) : 
    m_name_m(name_m), m_out(0) {
    m_gen_decl = false;
    m_scope_depth = 0;

}

TaskGenerateFunctionEmbeddedC::~TaskGenerateFunctionEmbeddedC() {


}

void TaskGenerateFunctionEmbeddedC::generate(
    IOutput                         *out_def,
    arl::dm::IDataTypeFunction      *func) {
    m_gen_decl = false;

    m_out = out_def;
    func->accept(m_this);
}

void TaskGenerateFunctionEmbeddedC::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) {
    m_scope_depth = 0;
    m_out->indent();

    m_scope_s.push_back(t->getBody());

    if (t->getReturnType()) {
        t->getReturnType()->accept(m_this);
        m_out->write(" ");
    } else {
        m_out->write("void ");
    }

    m_out->write("%s(", m_name_m->getName(t).c_str());

    TaskGenerateEmbCDataType dt_gen(m_out, m_name_m);
    if (t->getParameters().size() > 0) {
        m_out->write("\n");
        m_out->inc_ind();
        m_out->inc_ind();
        for (uint32_t i=0; i<t->getParameters().size(); i++) {
            m_out->indent();
            dt_gen.generate(t->getParameters().at(i)->getDataType());
            m_out->write(" %s", t->getParameters().at(i)->name().c_str());
            if (i+1 < t->getParameters().size()) {
                m_out->write(",\n");
            }
        }
        m_out->dec_ind();
        m_out->dec_ind();
    } else {
        // No parameters. 
        m_out->write("void");
    }

    m_out->write(") {\n");

    m_out->inc_ind();
    t->getBody()->accept(m_this);
    m_out->dec_ind();

    m_out->println("}");

    m_scope_s.pop_back();
}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtAssign(ITypeProcStmtAssign *s) {
    std::map<TypeProcStmtAssignOp,std::string> op_m = {
        {TypeProcStmtAssignOp::Eq, "="},
        {TypeProcStmtAssignOp::PlusEq, "+="},
        {TypeProcStmtAssignOp::MinusEq, "-="},
        {TypeProcStmtAssignOp::ShlEq, "<<="},
        {TypeProcStmtAssignOp::ShrEq, ">>="},
        {TypeProcStmtAssignOp::OrEq, "|="},
        {TypeProcStmtAssignOp::AndEq, "&="}
    };
    TaskGenerateEmbCExpr expr_gen(m_name_m);

    m_out->indent();
    expr_gen.generate(m_out, 0, m_scope_s.back(), s->getLhs());
    m_out->write(" %s ", op_m.find(s->op())->second.c_str());
    expr_gen.generate(m_out, 0, m_scope_s.back(), s->getRhs());
    m_out->write(";\n");
}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtBreak(ITypeProcStmtBreak *s) {
    m_out->println("break;");
}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtContinue(ITypeProcStmtContinue *s) {
    m_out->println("continue;");

}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtForeach(ITypeProcStmtForeach *s) {

}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtIfElse(ITypeProcStmtIfElse *s) {
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

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtMatch(ITypeProcStmtMatch *s) {

}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtRepeat(ITypeProcStmtRepeat *s) {
    if (m_gen_decl) {
        return;
    }

}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtRepeatWhile(ITypeProcStmtRepeatWhile *s) {
    if (m_gen_decl) {
        return;
    }

}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtReturn(ITypeProcStmtReturn *s) {
    if (m_gen_decl) {
        return;
    }

    if (s->getExpr()) {
        m_out->print("return ");
        m_out->write(";\n");
    } else {
        m_out->println("return;");
    }
}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtScope(ITypeProcStmtScope *s) {
    if (m_gen_decl) {
        // Avoid recursing deeper when generating declarations
        return;
    }

    if (m_scope_s.size() > 1) {
        m_out->println("{");
        m_out->inc_ind();
    }

    // Generate all in-scope declarations at the beginning of the scope
    m_gen_decl = true;
    TaskGenerateEmbCVarDecl decl_gen(m_out, m_name_m);
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

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtVarDecl(ITypeProcStmtVarDecl *s) {
    // Ignore here. Handled by the containing scope
}

void TaskGenerateFunctionEmbeddedC::visitTypeProcStmtWhile(ITypeProcStmtWhile *s) {

}

}
}
}
