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
        TaskGenerateLocals(m_ctxt, m_out).generate(it->get());
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
                
                // TODO: initialize fields
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

}
}
}
