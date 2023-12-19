/*
 * TaskGenerateEmbCRegGroup.cpp
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
#include <algorithm>
#include "dmgr/impl/DebugMacros.h"
#include "vsc/dm/impl/TaskComputeTypePackedSize.h"
#include "TaskGenerateEmbCRegGroup.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCRegGroup::TaskGenerateEmbCRegGroup(
    IContext                *ctxt,
    IOutput                 *out) : m_ctxt(ctxt), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateEmbCRegGroup", m_ctxt->getDebugMgr());
}

TaskGenerateEmbCRegGroup::~TaskGenerateEmbCRegGroup() {

}

void TaskGenerateEmbCRegGroup::generate(arl::dm::IDataTypeRegGroup *t) {
    m_next_offset = 0;

    // Collect up the fields
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }

    // Now, sort by offset
    std::sort(m_fields.begin(), m_fields.end(), [&](
        arl::dm::ITypeFieldReg *r1,
        arl::dm::ITypeFieldReg *r2) {
            return r1->getAddrOffset() < r2->getAddrOffset();
        });
    m_out->println("typedef struct %s_s {", 
        m_ctxt->nameMap()->getName(t).c_str());
    m_out->inc_ind();
    int64_t next_offset = 0;
    int32_t res_id = 1;
    int32_t max_bitsz = 0;
    for (std::vector<arl::dm::ITypeFieldReg *>::const_iterator
        it=m_fields.begin();
        it!=m_fields.end(); it++) {
        (*it)->getDataType()->accept(m_this);
        if (m_bitsz > max_bitsz) {
            max_bitsz = m_bitsz;
        }
    }

    for (std::vector<arl::dm::ITypeFieldReg *>::const_iterator
        it=m_fields.begin();
        it!=m_fields.end(); it++) {
        if ((*it)->getAddrOffset() > next_offset) {
            m_out->println("uint8_t res%d[%d];", res_id, 
                ((*it)->getAddrOffset()-next_offset));
        }

        m_struct_t = 0;
        (*it)->getDataType()->accept(m_this);

        if (m_struct_t) {
            m_out->println("%s %s;", 
                m_ctxt->nameMap()->getName(m_struct_t).c_str(), 
                (*it)->name().c_str());
        } else {
            if (m_bitsz > 32) {
                m_out->println("uint64_t %s;", (*it)->name().c_str());
            } else if (m_bitsz > 16) {
                m_out->println("uint32_t %s;", (*it)->name().c_str());
            } else if (m_bitsz > 8) {
                m_out->println("uint16_t %s;", (*it)->name().c_str());
            } else {
                m_out->println("uint8_t %s;", (*it)->name().c_str());
            }
        }

        int32_t bit_sz = vsc::dm::TaskComputeTypePackedSize().compute(
            (*it)->getDataType());
        next_offset = (*it)->getAddrOffset()+(bit_sz/8);
    }
    m_out->dec_ind();
    m_out->println("} %s;", m_ctxt->nameMap()->getName(t).c_str());
}

void TaskGenerateEmbCRegGroup::visitDataTypeBool(vsc::dm::IDataTypeBool *t) { 
    DEBUG_ENTER("visitDataTypeBool");
    m_bitsz = 1;
    DEBUG_LEAVE("visitDataTypeBool");
}

void TaskGenerateEmbCRegGroup::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) { 
    DEBUG_ENTER("visitDataTypeEnum");
    m_bitsz = 32;
    DEBUG_LEAVE("visitDataTypeEnum");
}

void TaskGenerateEmbCRegGroup::visitDataTypeInt(vsc::dm::IDataTypeInt *t) { 
    DEBUG_ENTER("visitDataTypeInt");
    m_bitsz = t->getWidth();
    DEBUG_LEAVE("visitDataTypeInt");
}

void TaskGenerateEmbCRegGroup::visitDataTypeString(vsc::dm::IDataTypeString *t) { 
    DEBUG_ENTER("visitDataTypeString");
    m_bitsz = 8*sizeof(void *);
    DEBUG_LEAVE("visitDataTypeString");
}

void TaskGenerateEmbCRegGroup::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) { 
    DEBUG_ENTER("visitDataTypeStruct");

    DEBUG_LEAVE("visitDataTypeStruct");
}

void TaskGenerateEmbCRegGroup::visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) { 
    DEBUG_ENTER("visitDataTypePackedStruct");
    m_struct_t = t;
    m_bitsz = vsc::dm::TaskComputeTypePackedSize().compute(t);
    DEBUG_LEAVE("visitDataTypePackedStruct");
}

void TaskGenerateEmbCRegGroup::visitTypeFieldReg(arl::dm::ITypeFieldReg *f) {
    DEBUG_ENTER("visitTypeFieldReg");
    m_fields.push_back(f);
    DEBUG_LEAVE("visitTypeFieldReg");
}

dmgr::IDebug *TaskGenerateEmbCRegGroup::m_dbg = 0;

}
}
}
