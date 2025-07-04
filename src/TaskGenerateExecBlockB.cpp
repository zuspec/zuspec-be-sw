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
#include "TaskGenerateExecBlockB.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExprParamNB.h"
#include "TaskGenerateExecScopeB.h"
#include "TaskGenerateExecScopeNB.h"
#include "TaskGenerateExprB.h"
#include "TaskGenerateLocals.h"
#include "TaskCheckIsExecBlocking.h"
#include "TaskBuildAsyncScopeGroup.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecBlockB::TaskGenerateExecBlockB(
    IContext                        *ctxt, 
    IGenRefExpr                     *refgen,
    IOutput                         *out_h,
    IOutput                         *out_c) :
    m_ctxt(ctxt), m_refgen(refgen), m_out_h(out_h), m_out_c(out_c),
    m_expr_terminated(false) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecBlockB", m_ctxt->getDebugMgr());
}

TaskGenerateExecBlockB::~TaskGenerateExecBlockB() {

}

void TaskGenerateExecBlockB::generate(
        const std::string                           &fname,
        const std::string                           &tname,
        const std::vector<arl::dm::ITypeExecUP>     &execs) {
    int32_t idx = 0;

    // Add a new namespace for the locals
    m_ctxt->nameMap()->push();

    if (execs.size() == 1) {
        TypeProcStmtAsyncScopeGroupUP group(
            TaskBuildAsyncScopeGroup(m_ctxt).build(execs.front().get()));
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
        m_out_c->println("model_api_t *__api = 0;");

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

    }
    
    m_ctxt->nameMap()->pop();

}

void TaskGenerateExecBlockB::visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *s) {
    DEBUG_ENTER("visitTypeProcStmtAsyncScope");
    if (s->id() != -1) {
        m_out_c->println("case %d: {", s->id());
        m_out_c->inc_ind();
        m_out_c->println("CASE_%d:", s->id());
    } else {
        m_out_c->println("default: {");
        m_out_c->inc_ind();
        m_out_c->println("CASE_DEFAULT:");
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

    m_out_c->dec_ind();
    m_out_c->println("}");
    DEBUG_LEAVE("visitTypeProcStmtAsyncScope");
}

void TaskGenerateExecBlockB::visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) {
    DEBUG_ENTER("visitTypeProcStmtExpr");
    m_expr_terminated = false;
    m_out_c->indent();
    s->getExpr()->accept(m_this);
    if (!m_expr_terminated) {
        m_out_c->write(";\n");
    }
    DEBUG_LEAVE("visitTypeProcStmtExpr");
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

dmgr::IDebug *TaskGenerateExecBlockB::m_dbg = 0;


}
}
}
