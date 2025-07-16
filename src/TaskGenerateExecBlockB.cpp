/*
 * TaskGenerateExecBlockB.cpp
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
#include "ITaskGenerateExecModelCustomGen.h"
#include "OutputStr.h"
#include "ScopeLocalsAssociatedData.h"
#include "TaskGenerateExecBlockB.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExprParamNB.h"
#include "TaskGenerateExecScopeB.h"
#include "TaskGenerateExecScopeNB.h"
#include "TaskGenerateExprB.h"
#include "TaskGenerateLocals.h"
#include "TaskCheckIsExecBlocking.h"
#include "TaskBuildAsyncScopeGroup.h"
#include "TypeProcStmtGotoAsyncScope.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecBlockB::TaskGenerateExecBlockB(
    IContext                        *ctxt, 
    IGenRefExpr                     *refgen,
    IOutput                         *out_h,
    IOutput                         *out_c,
    const std::string               &fname) : 
    TaskGenerateAsyncBase(ctxt, refgen, out_c, fname), m_out_h(out_h) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecBlockB", m_ctxt->getDebugMgr());
}

TaskGenerateExecBlockB::~TaskGenerateExecBlockB() {

}

void TaskGenerateExecBlockB::generate(
        const std::vector<arl::dm::ITypeExecUP>     &execs) {

    if (execs.size() == 1) {

    } else if (execs.size() > 1) {
        // Multiple functions
        // Want a single top-level function that invokes the sub-functions
        TaskGenerateAsyncBase::generate(execs.front().get());
    } else { // zero -- stub out function
        m_out->println("static zsp_frame_t *%s(zsp_thread_t *thread, int32_t idx, va_list *args) {", m_fname.c_str());
        m_out->inc_ind();

        m_out->println("zsp_frame_t *ret = zsp_thread_alloc_frame(thread, 16, 0);");
        m_out->println("ret = zsp_thread_return(thread, 0);");
        m_out->println("return ret;");

        m_out->dec_ind();
        m_out->println("}");
    }
}

void TaskGenerateExecBlockB::visitTypeProcStmtAssign(arl::dm::ITypeProcStmtAssign *s) {
    DEBUG_ENTER("visitTypeProcStmtAssign");
    enter_stmt(s);
    m_out->indent();
    TaskGenerateExprNB(m_ctxt, m_refgen, m_out).generate(s->getLhs());

    switch (s->op()) {
        case arl::dm::TypeProcStmtAssignOp::Eq: m_out->write(" = "); break;
        case arl::dm::TypeProcStmtAssignOp::PlusEq: m_out->write(" += "); break;
        case arl::dm::TypeProcStmtAssignOp::MinusEq: m_out->write(" -= "); break;
        case arl::dm::TypeProcStmtAssignOp::ShlEq: m_out->write(" <<= "); break;
        case arl::dm::TypeProcStmtAssignOp::ShrEq: m_out->write(" >>= "); break;
        case arl::dm::TypeProcStmtAssignOp::OrEq: m_out->write(" |= "); break;
        case arl::dm::TypeProcStmtAssignOp::AndEq: m_out->write(" &= "); break;
    }

    TaskGenerateExprNB(m_ctxt, m_refgen, m_out).generate(s->getRhs());
    m_out->write(";\n");

    DEBUG_LEAVE("visitTypeProcStmtAssign");
}

void TaskGenerateExecBlockB::visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *s) {
    DEBUG_ENTER("visitTypeProcStmtAsyncScope");
    ScopeLocalsAssociatedData *scope = 
        dynamic_cast<ScopeLocalsAssociatedData *>(s->getAssociatedData());

    if (s->id() != -1) {
        m_out->println("case %d: {", s->id());
        m_out->inc_ind();
        m_out->println("CASE_%d:", s->id());
        m_next_scope_id = s->id()+1;
    } else {
        m_out->println("default: {");
        m_out->inc_ind();
        m_out->println("CASE_DEFAULT:");
        m_next_scope_id = -2;
    }

    m_scope_s.clear();
    for (std::vector<vsc::dm::ITypeVarScope *>::const_iterator
        it=scope->scopes().begin();
        it!=scope->scopes().end(); it++) {
        m_scope_s.push_back(*it);
        m_refgen->pushScope(*it);
    }

    if (s->id() == 0) {
        // Entry scope is unique in that we must grab parameters
        m_out->println("%s_t *__locals;", m_ctxt->nameMap()->getName(scope->type()).c_str());
        m_out->println("ret = zsp_thread_alloc_frame(thread, sizeof(%s_t), &%s);",
            m_ctxt->nameMap()->getName(m_largest_locals).c_str(),
            m_fname.c_str());
        m_out->println("__locals = zsp_frame_locals(ret, %s_t);",
            m_ctxt->nameMap()->getName(scope->type()).c_str());
        m_out->println("__locals->__exec_b = va_arg(*args, zsp_executor_t *);");
        m_out->println("__locals->__api = (model_api_t *)__locals->__exec_b->api;");
    } else {
        if (scope) {
            for (std::vector<vsc::dm::ITypeVarScope *>::const_iterator
                it=scope->scopes().begin();
                it!=scope->scopes().end(); it++) {
                ScopeLocalsAssociatedData *data = dynamic_cast<ScopeLocalsAssociatedData *>(
                    (*it)->getAssociatedData());
                if (it != scope->scopes().begin()) {
                    m_out->println("{");
                    m_out->inc_ind();
                }
                m_out->println("%s_t *__locals = zsp_frame_locals(ret, %s_t);", 
                    m_ctxt->nameMap()->getName(data->type()).c_str(),
                    m_ctxt->nameMap()->getName(data->type()).c_str());
            }
        }
    }

    for (std::vector<arl::dm::ITypeProcStmtUP>::const_iterator
        it=s->getStatements().begin();
        it!=s->getStatements().end(); it++) {
        (*it)->accept(m_this);
    }
    if (s->id() == -1) {
        // Check whether the function has explicitly returned. 
        // If not, then perform a default termination
        m_out->println("if (ret == thread->leaf) {");
        m_out->inc_ind();
        m_out->println("ret = zsp_thread_return(thread, 0);");
        m_out->dec_ind();
        m_out->println("}");
    }

    for (std::vector<vsc::dm::ITypeVarScope *>::const_iterator
        it=m_scope_s.begin();
        it!=m_scope_s.end(); it++) {
        m_refgen->popScope();
        m_out->dec_ind();
        m_out->println("}");
    }

    // m_out->dec_ind();
    // m_out->println("}");
    DEBUG_LEAVE("visitTypeProcStmtAsyncScope");
}

void TaskGenerateExecBlockB::visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) {
    DEBUG_ENTER("visitTypeProcStmtExpr");
    // Ensure we're in the right scope
    enter_stmt(s);
    m_expr_terminated = false;
    m_out->indent();
    s->getExpr()->accept(m_this);
    if (!m_expr_terminated) {
        m_out->write(";\n");
    }
//    leave_stmt(s);
    DEBUG_LEAVE("visitTypeProcStmtExpr");
}

void TaskGenerateExecBlockB::visitTypeProcStmtGotoAsyncScope(TypeProcStmtGotoAsyncScope *s) {
    DEBUG_ENTER("visitTypeProcStmtGotoAsyncScope");
    m_out->println("goto CASE_%d;", s->target()->id());
    DEBUG_LEAVE("visitTypeProcStmtGotoAsyncScope");
}

void TaskGenerateExecBlockB::visitTypeProcStmtIfElse(arl::dm::ITypeProcStmtIfElse *s) {
    DEBUG_ENTER("visitTypeProcStmtIfElse");
    enter_stmt(s);
    for (std::vector<arl::dm::ITypeProcStmtIfClauseUP>::const_iterator
        it=s->getIfClauses().begin();
        it!=s->getIfClauses().end(); it++) {
        m_out->indent();
        if (it == s->getIfClauses().begin()) {
            m_out->write("if (");
        } else {
            m_out->write("} else if (");
        }
        TaskGenerateExprNB(m_ctxt, m_refgen, m_out).generate((*it)->getCond());
        m_out->write(") {\n");
        m_out->inc_ind();
        (*it)->getStmt()->accept(m_this);
        m_out->dec_ind();
    }

    if (s->getElseClause()) {
        m_out->println("} else {");
    } else {
        m_out->println("}");
    }
    DEBUG_LEAVE("visitTypeProcStmtIfElse");
}

void TaskGenerateExecBlockB::visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) {
    DEBUG_ENTER("visitTypeProcStmtRepeat");
    m_refgen->pushScope(s);

    m_refgen->popScope();
    DEBUG_LEAVE("visitTypeProcStmtRepeat");
}

void TaskGenerateExecBlockB::visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) {
    DEBUG_ENTER("visitTypeProcStmtScope");
    enter_stmt(s);
    VisitorBase::visitTypeProcStmtScope(s);
    DEBUG_LEAVE("visitTypeProcStmtScope");
}

void TaskGenerateExecBlockB::visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) {
    DEBUG_ENTER("visitTypeExprMethodCallContext");

    ITaskGenerateExecModelCustomGen *custom_gen = 
        dynamic_cast<ITaskGenerateExecModelCustomGen *>(e->getTarget()->getAssociatedData());

    DEBUG("custom_gen: %p (%p)", custom_gen, e->getTarget()->getAssociatedData());
    if (custom_gen) {
        custom_gen->genExprMethodCallContextB(
            m_ctxt,
            m_out,
            m_refgen,
            e);
    } else {
        m_out->write("%s(", 
            m_ctxt->nameMap()->getName(e->getTarget()).c_str()
        );
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            if (it != e->getParameters().begin()) {
                m_out->write(", ");
            }
            TaskGenerateExecModelExprParamNB(m_ctxt, m_refgen, m_out).generate(
                it->get()
            );
        }
        m_out->write(")");
    }
    m_expr_terminated = true;
    DEBUG_LEAVE("visitTypeExprMethodCallContext");
}

void TaskGenerateExecBlockB::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) {
    DEBUG_ENTER("visitTypeExprMethodCallStatic");
    ITaskGenerateExecModelCustomGen *custom_gen = 
        dynamic_cast<ITaskGenerateExecModelCustomGen *>(e->getTarget()->getAssociatedData());

    m_out->write("ret->idx = %d;\n", m_next_scope_id);

    if (custom_gen) {
        custom_gen->genExprMethodCallStaticB(
            m_ctxt,
            m_out,
            m_refgen,
            e);
    } else {
        m_out->write("%s(", 
            m_ctxt->nameMap()->getName(e->getTarget()).c_str()
        );
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            if (it != e->getParameters().begin()) {
                m_out->write(", ");
            }
            TaskGenerateExecModelExprParamNB(m_ctxt, m_refgen, m_out).generate(it->get());
        }
        m_out->write(")");
    }
    m_expr_terminated = true;
    DEBUG_LEAVE("visitTypeExprMethodCallStatic");
}


}
}
}
