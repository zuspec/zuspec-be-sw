/*
 * TaskGenerateActionQueueCalls.cpp
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

#include "dmgr/impl/DebugMacros.h"
#include "TaskGenerateActionQueueCalls.h"
#include "TaskGenerateEmbCDataType.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateActionQueueCalls::TaskGenerateActionQueueCalls(
    dmgr::IDebugMgr                     *dmgr,
    NameMap                             *name_m,
    IModelFieldComponentRoot            *root) : 
        m_dmgr(dmgr), m_name_m(name_m), m_root(root) {
    DEBUG_INIT("TaskGenerateActionQueueCalls", dmgr);
}

TaskGenerateActionQueueCalls::~TaskGenerateActionQueueCalls() {

}

void TaskGenerateActionQueueCalls::generate(
        IOutput                                     *out,
        const std::vector<ExecutorActionQueueEntry> &ops) {
    m_out = out;

    for (std::vector<ExecutorActionQueueEntry>::const_iterator
        it=ops.begin();
        it!=ops.end(); it++) {
        switch (it->kind) {
            case ExecutorActionQueueEntryKind::Action: {
                out->println("{");
                out->inc_ind();
                out->indent();
                TaskGenerateEmbCDataType(out, m_name_m).generate(
                    it->action->getDataTypeT<vsc::dm::IDataTypeStruct>());
                out->write(" ctx = {\n");
                out->inc_ind();
                enter_field_scope();
                for (std::vector<vsc::dm::IModelFieldUP>::const_iterator
                    f_it=it->action->fields().begin();
                    f_it!=it->action->fields().end(); f_it++) {
                    (*f_it)->accept(m_this);
                }
                leave_field_scope();
                out->write("\n");
                out->dec_ind();
                out->println("};");
                out->println("action_%s_exec(&ctx);", m_name_m->getName(
                    it->action->getDataTypeT<vsc::dm::IDataTypeStruct>()).c_str());
                out->dec_ind();
                out->println("}");
            } break;

            case ExecutorActionQueueEntryKind::Depend: {
                out->println("// Depend (%d,%d)", it->executor_id, it->action_id);
            } break;

            case ExecutorActionQueueEntryKind::Notify: {
                out->println("// Notify %d", it->action_id);
            } break;
        }
    }
}

void TaskGenerateActionQueueCalls::visitModelField(vsc::dm::IModelField *f) {
    DEBUG_ENTER("visitModelField %s", f->name().c_str());
    m_field_s.push_back(f);
    if (need_comma()) {
        m_out->write(", ");
    }
    f->getDataType()->accept(m_this);
    field_generated();
    m_field_s.pop_back();
    DEBUG_LEAVE("visitModelField %s", f->name().c_str());
}

void TaskGenerateActionQueueCalls::visitModelFieldRef(vsc::dm::IModelFieldRef *f) {
    DEBUG_ENTER("visitModelFieldRef");
    // TODO: need to determine cases in which to abort entirely

    m_isref_s.push_back(true);
    m_field_s.push_back(f);
    m_field_s.push_back(f->getRef());
    if (need_comma()) {
        m_out->write(", ");
    }
    f->getDataType()->accept(m_this);
    field_generated();
    m_field_s.pop_back();
    m_field_s.pop_back();
    DEBUG_LEAVE("visitModelFieldRef");
}

void TaskGenerateActionQueueCalls::visitModelFieldExecutor(arl::dm::IModelFieldExecutor *f) {
    // Ignore
}

void TaskGenerateActionQueueCalls::visitModelFieldExecutorClaim(IModelFieldExecutorClaim *f) {
    if (need_comma()) {
        m_out->write(", ");
    }
    m_out->write("%s.%s=0", 
        is_first()?m_out->ind():"",
        f->name().c_str());
    field_generated();
}

void TaskGenerateActionQueueCalls::visitDataTypeComponent(IDataTypeComponent *t) {
    const std::vector<int32_t> &path = m_root->getCompInstPath(
        dynamic_cast<IModelFieldComponent *>(m_field_s.back()));
    m_out->write("%s.%s=&comp_tree", 
        (is_first())?m_out->ind():"",
        m_field_s.at(m_field_s.size()-2)->name().c_str());

    IModelFieldComponent *comp = m_root;
    for (std::vector<int32_t>::const_iterator
        it=path.begin();
        it!=path.end(); it++) {
        m_out->write(".");
        comp = comp->getFieldT<IModelFieldComponent>(*it);
        m_out->write("%s", comp->name().c_str());
    }
    field_generated();
}

void TaskGenerateActionQueueCalls::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {
    // TODO: value
    m_out->print(".%s=TODO", m_field_s.back()->name().c_str());
    field_generated();
}

void TaskGenerateActionQueueCalls::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    DEBUG_ENTER("visitDataTypeInt");
    if (t->is_signed()) {
        m_out->write("%s.%s=%lld", 
            is_first()?m_out->ind():"",
            m_field_s.back()->name().c_str(),
            m_field_s.back()->val()->val_i());
    } else {
        m_out->write("%s.%s=0x%llx", 
            is_first()?m_out->ind():"",
            m_field_s.back()->name().c_str(),
            m_field_s.back()->val()->val_u());
    }
    DEBUG_LEAVE("visitDataTypeInt");
}

void TaskGenerateActionQueueCalls::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());
    m_out->write("%s.%s={\n", 
        is_first()?m_out->ind():"",
        m_field_s.back()->name().c_str());
    m_out->inc_ind();
    enter_field_scope();
    for (uint32_t i=0; i<t->getFields().size(); i++) {
        m_field_s.back()->fields().at(i)->accept(m_this);
    }
    leave_field_scope();
    m_out->write("\n");
    m_out->dec_ind();
    m_out->println("}");
    DEBUG_LEAVE("visitDataTypeStruct %s", t->name().c_str());
}

bool TaskGenerateActionQueueCalls::need_comma() {
    if (m_field_count_last != m_field_count_s.back()) {
        m_field_count_last = m_field_count_s.back();
        return true;
    } else {
        return false;
    }
}

void TaskGenerateActionQueueCalls::enter_field_scope() {
    m_field_count_s.push_back(0);
    m_field_count_last = 0;
}

void TaskGenerateActionQueueCalls::leave_field_scope() {
    m_field_count_s.pop_back();
    m_field_count_last = (m_field_count_s.size())?m_field_count_s.back():0;
}

void TaskGenerateActionQueueCalls::field_generated() {
    m_field_count_s.back() += 1;
}

bool TaskGenerateActionQueueCalls::is_first() {
    return m_field_count_s.back() == 0;
}

dmgr::IDebug *TaskGenerateActionQueueCalls::m_dbg = 0;

}
}
}
