/*
 * TaskGenerateEmbCStruct.cpp
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
#include "TaskGenerateEmbCStruct.h"
#include "TaskGenerateEmbCVarDecl.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCStruct::TaskGenerateEmbCStruct(
    IContext                *ctxt,
    IOutput                 *out) : m_ctxt(ctxt), m_out(out),
        m_mangler(ctxt->getDebugMgr(), ctxt->nameMap()) {
    DEBUG_INIT("TaskGenerateEmbCStruct", ctxt->getDebugMgr());
}

TaskGenerateEmbCStruct::~TaskGenerateEmbCStruct() {

}

void TaskGenerateEmbCStruct::generate(vsc::dm::IDataTypeStruct *type) {
    m_depth = 0;

    type->accept(m_this);

    // Ensure we're working with a properly-mangled name
    m_mangler.mangle(type);

    m_out->println("typedef struct %s_s {", m_ctxt->nameMap()->getName(type).c_str());
    m_out->inc_ind();
    m_depth++;
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=type->getFields().begin();
        it!=type->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_depth--;
    m_out->dec_ind();
    m_out->println("} %s;", m_ctxt->nameMap()->getName(type).c_str());
    m_out->println("");
    m_ignore_field_s.clear();
}

void TaskGenerateEmbCStruct::visitTypeFieldExecutor(arl::dm::ITypeFieldExecutor *f) {
    // Ignore
}

void TaskGenerateEmbCStruct::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) {
    if (!m_ignore_field_s.size() || 
        m_ignore_field_s.back()->find(f->name()) == m_ignore_field_s.back()->end()) {
        m_field_s.push_back(f);
        m_ref_s.push_back(false);
        f->getDataType()->accept(m_this);
        m_ref_s.pop_back();
        m_field_s.pop_back();
    }
}

void TaskGenerateEmbCStruct::visitTypeFieldPool(arl::dm::ITypeFieldPool *f) {
    if (!m_ignore_field_s.size() || 
        m_ignore_field_s.back()->find(f->name()) == m_ignore_field_s.back()->end()) {
        m_field_s.push_back(f);
        m_ref_s.push_back(false);
        f->getElemDataType()->accept(m_this);
        m_ref_s.pop_back();
        m_field_s.pop_back();
    }
}

void TaskGenerateEmbCStruct::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    if (!m_ignore_field_s.size() || 
        m_ignore_field_s.back()->find(f->name()) == m_ignore_field_s.back()->end()) {
        m_field_s.push_back(f);
        m_ref_s.push_back(true);
        f->getDataType()->accept(m_this);
        m_ref_s.pop_back();
        m_field_s.pop_back();
    }
}

void TaskGenerateEmbCStruct::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {
    if (m_depth) {
        TaskGenerateEmbCVarDecl(m_ctxt, m_out).generate(t, m_field_s.back());
    }
}

void TaskGenerateEmbCStruct::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    if (m_depth) {
        TaskGenerateEmbCVarDecl(m_ctxt, m_out).generate(t, m_field_s.back());
    }
}

void TaskGenerateEmbCStruct::visitDataTypeResource(arl::dm::IDataTypeResource *t) {
    if (!m_depth) {
        m_ignore_field_s.push_back(&m_ignore_resource_fields);
    } else {
        visitDataTypeStruct(t);
    }
}

void TaskGenerateEmbCStruct::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    if (m_depth) {
        TaskGenerateEmbCVarDecl(m_ctxt, m_out).generate(t, m_field_s.back());
    }
}


dmgr::IDebug *TaskGenerateEmbCStruct::m_dbg = 0;

std::set<std::string> TaskGenerateEmbCStruct::m_ignore_resource_fields = {
    "initial"
};

}
}
}
