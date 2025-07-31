/*
 * TaskGenerateAsyncBase.cpp
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
#include "TaskGenerateAsyncBase.h"
#include "TaskGenerateLocals.h"
#include "TypeProcStmtGotoAsyncScope.h"
#include "OutputStr.h"

namespace zsp {
namespace be {
namespace sw {


TaskGenerateAsyncBase::TaskGenerateAsyncBase(
    IContext            *ctxt,
    IGenRefExpr         *refgen,
    IOutput             *out,
    const std::string   &fname) :
        m_dbg(0), m_ctxt(ctxt), m_refgen(refgen), m_out(out), m_fname(fname) {

}

TaskGenerateAsyncBase::~TaskGenerateAsyncBase() {

}

void TaskGenerateAsyncBase::visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *s) {
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
        generate_init_locals();
        DEBUG("async new_scope=%d", scope->new_scope());
        init_locals(scope->type(), 0);
    } else {
        if (scope) {
            DEBUG("async new_scope=%d", scope->new_scope());
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

    for (std::vector<vsc::dm::IAcceptUP>::const_iterator
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

void TaskGenerateAsyncBase::visitTypeProcStmtGotoAsyncScope(TypeProcStmtGotoAsyncScope *s) {
    DEBUG_ENTER("visitTypeProcStmtGotoAsyncScope");
    m_out->println("goto CASE_%d;", s->target()->id());
    DEBUG_LEAVE("visitTypeProcStmtGotoAsyncScope");
}

void TaskGenerateAsyncBase::generate(vsc::dm::IAccept *it) {
    // Add a new namespace for the locals
    m_ctxt->nameMap()->push();

    TypeProcStmtAsyncScopeGroupUP group(TaskBuildAsyncScopeGroup(m_ctxt).build(it));
    m_largest_locals = group->largest_locals();
    OutputStr out(m_out->ind());

    m_out->println("static zsp_frame_t *%s(zsp_thread_t *thread, int32_t idx, va_list *args) {", 
        m_fname.c_str());
    m_out->inc_ind();
    // First things first: generate the locals structs
    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=group->localsTypes().begin();
        it!=group->localsTypes().end(); it++) {
        generate_locals(it->get());
    }
    m_out->println("zsp_frame_t *ret = thread->leaf;");

    m_out->println("switch(idx) {");
    m_out->inc_ind();
    for (std::vector<arl::dm::ITypeProcStmtUP>::const_iterator
        it=group->getStatements().begin();
        it!=group->getStatements().end(); it++) {
        DEBUG_ENTER("visit statement");
        (*it)->accept(m_this);
        DEBUG_LEAVE("visit statement");
    }

    m_out->dec_ind();
    m_out->println("}"); // end-switch

    m_out->println("return ret;");

    m_out->dec_ind();
    m_out->println("}");

    m_ctxt->nameMap()->pop();
}

void TaskGenerateAsyncBase::enter_stmt(arl::dm::ITypeProcStmt *s) {
    ScopeLocalsAssociatedData *data = 
        dynamic_cast<ScopeLocalsAssociatedData *>(s->getAssociatedData());
    DEBUG_ENTER("enter_stmt (%p %d)", data, data?data->scopes().size():-1);
    
    if (data) {
        DEBUG("new_scope=%d", data->new_scope());
        if (data->scopes().size() > m_scope_s.size()) {
            DEBUG("PUSH: ");
            for (uint32_t i=m_scope_s.size(); i<data->scopes().size(); i++) {
                m_refgen->pushScope(data->scopes().at(i));
                m_scope_s.push_back(data->scopes().at(i));
                m_out->println("{");
                m_out->inc_ind();
                m_out->println("%s_t *__locals = zsp_frame_locals(ret, %s_t);",
                    data->type()->name().c_str(),
                    data->type()->name().c_str());
            }

            if (data->new_scope()) {
                DEBUG("TODO: initialize fields");
            }
        } else if (data->scopes().size() < m_scope_s.size()) {
            DEBUG("POP: ");
            while (data->scopes().size() < m_scope_s.size()) {
                m_scope_s.pop_back();
                m_refgen->popScope();
                m_out->dec_ind();
                m_out->println("}");
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
        //                 m_out->print("{");
        //                 m_out->inc_ind();
        //             }
        //         } else {
        //             // Popping
        //             for (uint32_t i=data->scopes().size(); 
        //                 i<m_scope->scopes().size(); i++) {
        //                 m_refgen->popScope();
        //                 m_out->dec_ind();
        //                 m_out->print("}");
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

void TaskGenerateAsyncBase::init_locals(vsc::dm::IDataTypeStruct *t, int32_t start) {
    DEBUG_ENTER("init_locals %s start=%d", t->name().c_str(), start);

    for (uint32_t i=start; i<t->getFields().size(); i++) {
        DEBUG("Field: %s", t->getField(i)->name().c_str());
    }

    DEBUG_LEAVE("init_locals %s start=%d", t->name().c_str(), start);
}

}
}
}
