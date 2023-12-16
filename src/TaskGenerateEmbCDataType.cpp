/*
 * TaskGenerateEmbCDataType.cpp
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
#include "TaskGenerateEmbCDataType.h"

using namespace zsp::arl::dm;

namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCDataType::TaskGenerateEmbCDataType(
    IContext            *ctxt,
    IOutput             *out,
    bool                is_fparam) : 
    m_ctxt(ctxt), m_out(out), m_is_fparam(is_fparam) {
    DEBUG_INIT("zsp::be::sw""TaskGenerateEmbCDataType", ctxt->getDebugMgr());
}

TaskGenerateEmbCDataType::~TaskGenerateEmbCDataType() {

}

void TaskGenerateEmbCDataType::generate(vsc::dm::IDataType *type) {
    type->accept(m_this);
}

void TaskGenerateEmbCDataType::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {
    m_out->write("%s", m_ctxt->nameMap()->getName(t).c_str());
}

void TaskGenerateEmbCDataType::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    if (t->getWidth() <= 8) {
        m_out->write("%schar", (!t->is_signed())?"unsigned ":"");
    } else if (t->getWidth() <= 16) {
        m_out->write("%sshort", (!t->is_signed())?"unsigned ":"");
    } else if (t->getWidth() <= 32) {
        m_out->write("%sint", (!t->is_signed())?"unsigned ":"");
    } else if (t->getWidth() <= 64) {
        m_out->write("%slong long", (!t->is_signed())?"unsigned ":"");
    } else {
        // TODO: Fatal
    }
}

void TaskGenerateEmbCDataType::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    if (m_is_fparam) {
        m_out->write("%s *", m_ctxt->nameMap()->getName(t).c_str());
    } else {
        m_out->write("%s", m_ctxt->nameMap()->getName(t).c_str());
    }
}

void TaskGenerateEmbCDataType::visitTypeFieldPool(arl::dm::ITypeFieldPool *f) {
    // Each pool has its own 'pool' type. Bypass this reported
    // type and use the pool-item type instead
    f->getElemDataType()->accept(m_this);
}

dmgr::IDebug *TaskGenerateEmbCDataType::m_dbg = 0;

}
}
}
