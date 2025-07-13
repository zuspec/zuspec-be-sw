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
    IOutput                         *out_c) :
    m_ctxt(ctxt), m_refgen(refgen), m_out_h(out_h), m_out_c(out_c),
    m_expr_terminated(false), m_scope(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecBlockB", m_ctxt->getDebugMgr());
}

TaskGenerateExecBlockB::~TaskGenerateExecBlockB() {

}

void TaskGenerateExecBlockB::generate(
        const std::string                           &fname,
        const std::string                           &tname,
        const std::vector<arl::dm::ITypeExecUP>     &execs) {
    int32_t idx = 0;
    m_fname = fname;

    // Add a new namespace for the locals
    m_ctxt->nameMap()->push();

    if (execs.size() == 1) {
        TypeProcStmtAsyncScopeGroupUP group(
            TaskBuildAsyncScopeGroup(m_ctxt).build(execs.front().get()));
        m_largest_locals = group->largest_locals();
        OutputStr out(m_out_c->ind());

        m_out_c->println("static zsp_frame_t *%s(zsp_thread_t *thread, int32_t idx, va_list *args) {", fname.c_str());
        m_out_c->inc_ind();
        // First things first: generate the locals structs
        for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
            it=group->localsTypes().begin();
            it!=group->localsTypes().end(); it++) {
            TaskGenerateLocals(m_ctxt, m_out_c).generate(it->get());
        }
        m_out_c->println("zsp_frame_t *ret = thread->leaf;");

        m_out_c->println("switch(idx) {");
        m_out_c->inc_ind();
        for (std::vector<arl::dm::ITypeProcStmtUP>::const_iterator
            it=group->getStatements().begin();
            it!=group->getStatements().end(); it++) {
            DEBUG_ENTER("visit statement");
            (*it)->accept(m_this);
            DEBUG_LEAVE("visit statement");
        }

        m_out_c->dec_ind();
        m_out_c->println("}"); // end-switch

        m_out_c->println("return ret;");

        m_out_c->dec_ind();
        m_out_c->println("}");
    } else if (execs.size() > 1) {
        // Multiple functions
        // Want a single top-level function that invokes the sub-functions
    } else { // zero -- stub out function
        m_out_c->println("static zsp_frame_t *%s(zsp_thread_t *thread, int32_t idx, va_list *args) {", fname.c_str());
        m_out_c->inc_ind();

        m_out_c->println("zsp_frame_t *ret = zsp_thread_alloc_frame(thread, 16, 0);");
        m_out_c->println("ret = zsp_thread_return(thread, 0);");
        m_out_c->println("return ret;");

        m_out_c->dec_ind();
        m_out_c->println("}");

    }
    
    m_ctxt->nameMap()->pop();

}

void TaskGenerateExecBlockB::visitTypeProcStmtAssign(arl::dm::ITypeProcStmtAssign *s) {
    DEBUG_ENTER("visitTypeProcStmtAssign");
    enter_stmt(s);
    m_out_c->indent();
    TaskGenerateExprNB(m_ctxt, m_refgen, m_out_c).generate(s->getLhs());

    switch (s->op()) {
        case arl::dm::TypeProcStmtAssignOp::Eq: m_out_c->write(" = "); break;
        case arl::dm::TypeProcStmtAssignOp::PlusEq: m_out_c->write(" += "); break;
        case arl::dm::TypeProcStmtAssignOp::MinusEq: m_out_c->write(" -= "); break;
        case arl::dm::TypeProcStmtAssignOp::ShlEq: m_out_c->write(" <<= "); break;
        case arl::dm::TypeProcStmtAssignOp::ShrEq: m_out_c->write(" >>= "); break;
        case arl::dm::TypeProcStmtAssignOp::OrEq: m_out_c->write(" |= "); break;
        case arl::dm::TypeProcStmtAssignOp::AndEq: m_out_c->write(" &= "); break;
    }

    TaskGenerateExprNB(m_ctxt, m_refgen, m_out_c).generate(s->getRhs());
    m_out_c->write(";\n");

    DEBUG_LEAVE("visitTypeProcStmtAssign");
}

void TaskGenerateExecBlockB::visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *s) {
    DEBUG_ENTER("visitTypeProcStmtAsyncScope");
    ScopeLocalsAssociatedData *scope = 
        dynamic_cast<ScopeLocalsAssociatedData *>(s->getAssociatedData());

    if (s->id() != -1) {
        m_out_c->println("case %d: {", s->id());
        m_out_c->inc_ind();
        m_out_c->println("CASE_%d:", s->id());
        m_next_scope_id = s->id()+1;
    } else {
        m_out_c->println("default: {");
        m_out_c->inc_ind();
        m_out_c->println("CASE_DEFAULT:");
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
        m_out_c->println("%s_t *__locals;", m_ctxt->nameMap()->getName(scope->type()).c_str());
        m_out_c->println("ret = zsp_thread_alloc_frame(thread, sizeof(%s_t), &%s);",
            m_ctxt->nameMap()->getName(m_largest_locals).c_str(),
            m_fname.c_str());
        m_out_c->println("__locals = zsp_frame_locals(ret, %s_t);",
            m_ctxt->nameMap()->getName(scope->type()).c_str());
        m_out_c->println("__locals->__exec_b = va_arg(*args, zsp_executor_t *);");
        m_out_c->println("__locals->__api = (model_api_t *)__locals->__exec_b->api;");
    } else {
        if (scope) {
            for (std::vector<vsc::dm::ITypeVarScope *>::const_iterator
                it=scope->scopes().begin();
                it!=scope->scopes().end(); it++) {
                ScopeLocalsAssociatedData *data = dynamic_cast<ScopeLocalsAssociatedData *>(
                    (*it)->getAssociatedData());
                if (it != scope->scopes().begin()) {
                    m_out_c->println("{");
                    m_out_c->inc_ind();
                }
                m_out_c->println("%s_t *__locals = zsp_frame_locals(ret, %s_t);", 
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
        m_out_c->println("if (ret == thread->leaf) {");
        m_out_c->inc_ind();
        m_out_c->println("ret = zsp_thread_return(thread, 0);");
        m_out_c->dec_ind();
        m_out_c->println("}");
    }

    for (std::vector<vsc::dm::ITypeVarScope *>::const_iterator
        it=m_scope_s.begin();
        it!=m_scope_s.end(); it++) {
        m_refgen->popScope();
        m_out_c->dec_ind();
        m_out_c->println("}");
    }

    // m_out_c->dec_ind();
    // m_out_c->println("}");
    DEBUG_LEAVE("visitTypeProcStmtAsyncScope");
}

void TaskGenerateExecBlockB::visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) {
    DEBUG_ENTER("visitTypeProcStmtExpr");
    // Ensure we're in the right scope
    enter_stmt(s);
    m_expr_terminated = false;
    m_out_c->indent();
    s->getExpr()->accept(m_this);
    if (!m_expr_terminated) {
        m_out_c->write(";\n");
    }
//    leave_stmt(s);
    DEBUG_LEAVE("visitTypeProcStmtExpr");
}

void TaskGenerateExecBlockB::visitTypeProcStmtGotoAsyncScope(TypeProcStmtGotoAsyncScope *s) {
    DEBUG_ENTER("visitTypeProcStmtGotoAsyncScope");
    m_out_c->println("goto CASE_%d;", s->target()->id());
    DEBUG_LEAVE("visitTypeProcStmtGotoAsyncScope");
}

void TaskGenerateExecBlockB::visitTypeProcStmtIfElse(arl::dm::ITypeProcStmtIfElse *s) {
    DEBUG_ENTER("visitTypeProcStmtIfElse");
    enter_stmt(s);
    for (std::vector<arl::dm::ITypeProcStmtIfClauseUP>::const_iterator
        it=s->getIfClauses().begin();
        it!=s->getIfClauses().end(); it++) {
        m_out_c->indent();
        if (it == s->getIfClauses().begin()) {
            m_out_c->write("if (");
        } else {
            m_out_c->write("} else if (");
        }
        TaskGenerateExprNB(m_ctxt, m_refgen, m_out_c).generate((*it)->getCond());
        m_out_c->write(") {\n");
        m_out_c->inc_ind();
        (*it)->getStmt()->accept(m_this);
        m_out_c->dec_ind();
    }

    if (s->getElseClause()) {
        m_out_c->println("} else {");
    } else {
        m_out_c->println("}");
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
            m_out_c,
            m_refgen,
            e);
    } else {
        m_out_c->write("%s(", 
            m_ctxt->nameMap()->getName(e->getTarget()).c_str()
        );
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            if (it != e->getParameters().begin()) {
                m_out_c->write(", ");
            }
            TaskGenerateExecModelExprParamNB(m_ctxt, m_refgen, m_out_c).generate(
                it->get()
            );
        }
        m_out_c->write(")");
    }
    m_expr_terminated = true;
    DEBUG_LEAVE("visitTypeExprMethodCallContext");
}

void TaskGenerateExecBlockB::visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) {
    DEBUG_ENTER("visitTypeExprMethodCallStatic");
    ITaskGenerateExecModelCustomGen *custom_gen = 
        dynamic_cast<ITaskGenerateExecModelCustomGen *>(e->getTarget()->getAssociatedData());

    m_out_c->write("ret->idx = %d;\n", m_next_scope_id);

    if (custom_gen) {
        custom_gen->genExprMethodCallStaticB(
            m_ctxt,
            m_out_c,
            m_refgen,
            e);
    } else {
        m_out_c->write("%s(", 
            m_ctxt->nameMap()->getName(e->getTarget()).c_str()
        );
        for (std::vector<vsc::dm::ITypeExprUP>::const_iterator
            it=e->getParameters().begin();
            it!=e->getParameters().end(); it++) {
            if (it != e->getParameters().begin()) {
                m_out_c->write(", ");
            }
            TaskGenerateExecModelExprParamNB(m_ctxt, m_refgen, m_out_c).generate(it->get());
        }
        m_out_c->write(")");
    }
    m_expr_terminated = true;
    DEBUG_LEAVE("visitTypeExprMethodCallStatic");
}

void TaskGenerateExecBlockB::enter_stmt(arl::dm::ITypeProcStmt *s) {
    ScopeLocalsAssociatedData *data = 
        dynamic_cast<ScopeLocalsAssociatedData *>(s->getAssociatedData());
    DEBUG_ENTER("enter_stmt (%p %d)", data, data?data->scopes().size():-1);
    
    if (data) {
        if (data->scopes().size() > m_scope_s.size()) {
            DEBUG("PUSH: ");
            for (uint32_t i=m_scope_s.size(); i<data->scopes().size(); i++) {
                m_refgen->pushScope(data->scopes().at(i));
                m_scope_s.push_back(data->scopes().at(i));
                m_out_c->println("{");
                m_out_c->inc_ind();
                m_out_c->println("%s_t *__locals = zsp_frame_locals(ret, %s_t);",
                    data->type()->name().c_str(),
                    data->type()->name().c_str());
                
                // TODO: initialize fields
            }
        } else if (data->scopes().size() < m_scope_s.size()) {
            DEBUG("POP: ");
            while (data->scopes().size() < m_scope_s.size()) {
                m_scope_s.pop_back();
                m_refgen->popScope();
                m_out_c->dec_ind();
                m_out_c->println("}");
            }
        } else if (data->scopes().back() != m_scope_s.back()) {
            DEBUG("SWAP: ");
        }
        // // Handle push-scope via entry
        // if (!m_scope || m_scope != data) {
        //     // New scope
        //     if (m_scope) {
        //         // See if we're pushing or popping
        //         if (data->scopes().size() > m_scope->scopes().size()) {
        //             // Pushing
        //             for (uint32_t i=m_scope->scopes().size(); 
        //                 i<data->scopes().size(); i++) {
        //                 m_refgen->pushScope(data->scopes().at(i));
        //                 m_out_c->print("{");
        //                 m_out_c->inc_ind();
        //             }
        //         } else {
        //             // Popping
        //             for (uint32_t i=data->scopes().size(); 
        //                 i<m_scope->scopes().size(); i++) {
        //                 m_refgen->popScope();
        //                 m_out_c->dec_ind();
        //                 m_out_c->print("}");
        //             }
        //         }
        //     } else {
        //         for (std::vector<vsc::dm::ITypeVarScope *>::const_iterator
        //             it=data->scopes().begin();
        //             it!=data->scopes().end(); it++) {
        //             m_refgen->pushScope(*it);
        //         }
        //     }
        //     m_scope = data;
        // }
    }

    DEBUG_LEAVE("enter_stmt");
}

dmgr::IDebug *TaskGenerateExecBlockB::m_dbg = 0;


}
}
}
