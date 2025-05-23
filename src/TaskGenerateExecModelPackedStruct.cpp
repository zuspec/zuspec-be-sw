/*
 * TaskGenerateExecModelPackedStruct.cpp
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
#include "zsp/arl/dm/impl/TaskGetTypeBitWidth.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelPackedStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelPackedStruct::TaskGenerateExecModelPackedStruct(
    IContext       *ctxt,
    IOutput        *out_h,
    IOutput        *out_c) : m_ctxt(ctxt), m_out_h(out_h), m_out_c(out_c) {

}

TaskGenerateExecModelPackedStruct::~TaskGenerateExecModelPackedStruct() {

}

void TaskGenerateExecModelPackedStruct::generate(arl::dm::IDataTypePackedStruct *t) {
    uint32_t n_bits = arl::dm::TaskGetTypeBitWidth().width(t);

    if (n_bits > 32) {
        m_base_t = "uint64_t";
    } else if (n_bits > 16) {
        m_base_t = "uint32_t";
    } else if (n_bits > 8) {
        m_base_t = "uint16_t";
    } else {
        m_base_t = "uint8_t";
    }

    m_out_h->println("typedef struct %s_s {", m_ctxt->nameMap()->getName(t).c_str());
    m_out_h->inc_ind();
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_out_h->dec_ind();
    m_out_h->println("} %s_t;", m_ctxt->nameMap()->getName(t).c_str());
    m_out_h->println("");
    m_out_h->println("typedef union {");
    m_out_h->inc_ind();
    m_out_h->println("%s v;", m_base_t.c_str());
    m_out_h->println("%s_t s;", m_ctxt->nameMap()->getName(t).c_str());
    m_out_h->dec_ind();
    m_out_h->println("} %s_u;", m_ctxt->nameMap()->getName(t).c_str());
}

void TaskGenerateExecModelPackedStruct::visitDataTypeBool(vsc::dm::IDataTypeBool *t) { 
    m_out_h->println("%s %s:1;",
        m_base_t.c_str(),
        m_field->name().c_str());
}

void TaskGenerateExecModelPackedStruct::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) { 
    m_out_h->println("%s %s:32;",
        m_base_t.c_str(),
        m_field->name().c_str());
}

void TaskGenerateExecModelPackedStruct::visitDataTypeInt(vsc::dm::IDataTypeInt *t) { 
    m_out_h->println("%s %s:%d;",
        m_base_t.c_str(),
        m_field->name().c_str(),
        t->getWidth());
}

void TaskGenerateExecModelPackedStruct::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    uint32_t n_bits = arl::dm::TaskGetTypeBitWidth().width(t);
    m_out_h->println("%s %s:%d;",
        m_base_t.c_str(),
        m_field->name().c_str(),
        n_bits);
}
    
void TaskGenerateExecModelPackedStruct::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) { 
    m_field = f;
    f->getDataType()->accept(m_this);
}
    
void TaskGenerateExecModelPackedStruct::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) { 
    m_field = f;
    f->getDataType()->accept(m_this);
}

dmgr::IDebug *TaskGenerateExecModelPackedStruct::m_dbg = 0;

}
}
}
