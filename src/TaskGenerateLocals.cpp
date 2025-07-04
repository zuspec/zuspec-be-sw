/*
 * TaskGenerateLocals.cpp
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
#include "TaskGenerateLocals.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateLocals::TaskGenerateLocals(
    IContext        *ctxt,
    IOutput         *out) : m_ctxt(ctxt), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateLocals", ctxt->getDebugMgr());
}

TaskGenerateLocals::~TaskGenerateLocals() {

}

void TaskGenerateLocals::generate(vsc::dm::IDataTypeStruct *t) {
    m_out->println("typedef struct %s_s {", m_ctxt->nameMap()->getName(t).c_str());
    m_out->inc_ind();
    m_out->println("zsp_executor_t *__exec_b;");
    m_out->println("model_api_t *__api;");
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_out->dec_ind();
    m_out->println("} %s_t;", m_ctxt->nameMap()->getName(t).c_str());

}

void TaskGenerateLocals::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    std::string tname;

    if (t->width() <= 8) {
        tname = (t->is_signed())?"int8_t":"uint8_t";
    } else if (t->width() <= 16) {
        tname = (t->is_signed())?"int16_t":"uint16_t";
    } else if (t->width() <= 32) {
        tname = (t->is_signed())?"int32_t":"uint32_t";
    } else {
        tname = (t->is_signed())?"int64_t":"uint64_t";
    }

    m_out->println("%s %s;", tname.c_str(), m_field->name().c_str());
}

void TaskGenerateLocals::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) {
    m_field = f;
    m_isref = false;
    f->getDataType()->accept(m_this);
}

void TaskGenerateLocals::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    m_field = f;
    m_isref = true;
    f->getDataType()->accept(m_this);
}

dmgr::IDebug *TaskGenerateLocals::m_dbg = 0;

}
}
}
