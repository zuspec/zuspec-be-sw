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
    dmgr::IDebugMgr         *dmgr,
    IOutput                 *out,
    NameMap                 *name_m) : m_out(out), m_name_m(name_m) {
    DEBUG_INIT("TaskGenerateEmbCStruct", dmgr);
}

TaskGenerateEmbCStruct::~TaskGenerateEmbCStruct() {

}

void TaskGenerateEmbCStruct::generate(vsc::dm::IDataTypeStruct *type) {

    m_out->println("typedef struct %s_s {", m_name_m->getName(type).c_str());
    m_out->inc_ind();
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=type->getFields().begin();
        it!=type->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_out->dec_ind();
    m_out->println("} %s;", m_name_m->getName(type).c_str());
    m_out->println("");
}

void TaskGenerateEmbCStruct::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) {
    m_field_s.push_back(f);
    m_ref_s.push_back(false);
    f->getDataType()->accept(m_this);
    m_ref_s.pop_back();
    m_field_s.pop_back();
}

void TaskGenerateEmbCStruct::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    m_field_s.push_back(f);
    m_ref_s.push_back(true);
    f->getDataType()->accept(m_this);
    m_ref_s.pop_back();
    m_field_s.pop_back();
}

void TaskGenerateEmbCStruct::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {
    TaskGenerateEmbCVarDecl(m_out, m_name_m).generate(t, m_field_s.back());
}

void TaskGenerateEmbCStruct::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    TaskGenerateEmbCVarDecl(m_out, m_name_m).generate(t, m_field_s.back());
}

void TaskGenerateEmbCStruct::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    TaskGenerateEmbCVarDecl(m_out, m_name_m).generate(t, m_field_s.back());
}

dmgr::IDebug *TaskGenerateEmbCStruct::m_dbg = 0;

}
}
}
