/*
 * TaskGenerateEmbCCompTreeData.cpp
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
#include "zsp/arl/dm/impl/IsResourcePool.h"
#include "TaskGenerateEmbCCompTreeData.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCCompTreeData::TaskGenerateEmbCCompTreeData(
    dmgr::IDebugMgr     *dmgr,
    IOutput             *out,
    NameMap             *name_m) : m_out(out), m_name_m(name_m) {
    DEBUG_INIT("TaskGenerateEmbCCompTreeData", dmgr);
}

TaskGenerateEmbCCompTreeData::~TaskGenerateEmbCCompTreeData() {

}

void TaskGenerateEmbCCompTreeData::generate(arl::dm::IModelFieldComponentRoot *root) {
    DEBUG_ENTER("generate");

    m_out->println("static %s comp_tree = {", 
        m_name_m->getName(root->getDataType()).c_str());
    m_out->inc_ind();
    int32_t last_field_count = 0;
    m_field_count_s.push_back(0);
    for (std::vector<vsc::dm::IModelFieldUP>::const_iterator
        it=root->getFields().begin();
        it!=root->getFields().end(); it++) {
        if (last_field_count != m_field_count_s.back()) {
            m_out->write(", ");
        }
        last_field_count = m_field_count_s.back();
        (*it)->accept(m_this);
    }
    m_field_count_s.pop_back();
    m_out->write("\n");
    m_out->dec_ind();
    m_out->println("};");

    DEBUG_LEAVE("generate");
}

void TaskGenerateEmbCCompTreeData::visitModelField(vsc::dm::IModelField *f) {
    DEBUG_ENTER("visitModelField %s", f->name().c_str());
    if (!m_ignore_field_s.size() || 
        !m_ignore_field_s.back() ||
        m_ignore_field_s.back()->find(f->name()) == m_ignore_field_s.back()->end()) {
        m_field_s.push_back(f);
        f->getDataType()->accept(m_this);
        m_field_count_s.back() += 1;
        m_field_s.pop_back();
    }
    DEBUG_LEAVE("visitModelField %s", f->name().c_str());
}

void TaskGenerateEmbCCompTreeData::visitModelFieldExecutor(arl::dm::IModelFieldExecutor *f) {
    // Ignore
}

void TaskGenerateEmbCCompTreeData::visitModelFieldPool(arl::dm::IModelFieldPool *f) {
    // Need to fill out resource array
    if (arl::dm::IsResourcePool().test(f)) {
        m_out->write("{");
        m_ignore_field_s.push_back(&m_ignore_field_resource);
        m_in_array_s.push_back(true);
        for (uint32_t i=0; i<f->getObjects().size(); i++) {
            m_field_s.push_back(f->getObjects().at(i).get());
            f->getDataTypePool()->accept(m_this);
            m_field_s.pop_back();
            if (i+1 < f->getObjects().size()) {
                m_out->write(",");
            }
        }
        m_out->write("},");
        m_in_array_s.pop_back();
        m_field_count_s.back() += 1;
        m_ignore_field_s.pop_back();
    }
}

void TaskGenerateEmbCCompTreeData::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {
    // TODO: value
    m_out->print(".%s=TODO", m_field_s.back()->name().c_str());
}

void TaskGenerateEmbCCompTreeData::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    DEBUG_ENTER("visitDataTypeInt");
#ifdef UNDEFINED
    if (t->is_signed()) {
        m_out->write("%s.%s=%lld", 
            (m_field_count_s.back())?"":m_out->ind(),
            m_field_s.back()->name().c_str(),
            m_field_s.back()->val()->val_i());
    } else {
        m_out->write("%s.%s=0x%llx", 
            (m_field_count_s.back())?"":m_out->ind(),
            m_field_s.back()->name().c_str(),
            m_field_s.back()->val()->val_u());
    }
#endif
    DEBUG_LEAVE("visitDataTypeInt");
}

void TaskGenerateEmbCCompTreeData::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());
    if (!m_in_array_s.size() || !m_in_array_s.back()) {
        m_out->write("%s.%s={\n", 
            (m_field_count_s.back())?"":m_out->ind(),
            m_field_s.back()->name().c_str());
    } else {
        m_out->write("{\n");
    }
    m_out->inc_ind();
    int32_t last_field_count = 0;
    m_field_count_s.push_back(0);
    for (uint32_t i=0; i<t->getFields().size(); i++) {
        if (i && m_field_count_s.back() != last_field_count) {
            m_out->write(", ");
            last_field_count = m_field_count_s.back();
        }
        m_field_s.back()->getFields().at(i)->accept(m_this);
    }
    m_field_count_s.pop_back();
    m_out->write("\n");
    m_out->dec_ind();
    m_out->println("}");
    DEBUG_LEAVE("visitDataTypeStruct %s", t->name().c_str());
}

dmgr::IDebug *TaskGenerateEmbCCompTreeData::m_dbg = 0;
std::set<std::string> TaskGenerateEmbCCompTreeData::m_ignore_field_resource = {
    "initial"
};

}
}
}
