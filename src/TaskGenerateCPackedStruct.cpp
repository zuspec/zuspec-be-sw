/*
 * TaskGenerateCPackedStruct.cpp
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
#include "TaskGenerateCPackedStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateCPackedStruct::TaskGenerateCPackedStruct(IContext *ctxt) : m_ctxt(ctxt) {
    

}

TaskGenerateCPackedStruct::~TaskGenerateCPackedStruct() {

}

void TaskGenerateCPackedStruct::generate(
        Output                          *out,
        arl::dm::IDataTypePackedStruct  *t) {
    m_out = out;
    m_bits = 0;

    switch (t->getByteSize()) {
        case 1: m_int_t = "int8_t"; break;
        case 2: m_int_t = "int16_t"; break;
        case 4: m_int_t = "int32_t"; break;
        case 8: m_int_t = "int64_t"; break;
        default: m_int_t = "int32_t"; break;
    }

    m_out->println("typedef union {");
    m_out->inc_ind();
    m_out->println("struct {");
    m_out->inc_ind();
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_out->dec_ind();
    m_out->println("} s;");

    if (m_bits > 64) {
        m_out->println("uint8_t v[%d];", ((m_bits-1)/8)+1);
    } else if (m_bits > 32) {
        m_out->println("uint64_t v;");
    } else if (m_bits > 16) {
        m_out->println("uint32_t v;");
    } else if (m_bits > 8) {
        m_out->println("uint16_t v;");
    } else {
        m_out->println("uint8_t v;");
    }

    m_out->dec_ind();
    m_out->println("} %s;", m_ctxt->nameMap()->getName(t).c_str());
}

void TaskGenerateCPackedStruct::visitDataTypeBool(vsc::dm::IDataTypeBool *t) {
    m_out->write("u%s", m_int_t.c_str());
    m_width = 1;
}

void TaskGenerateCPackedStruct::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {
    m_out->write("u%s", m_int_t.c_str());
    m_width = 32;
}

void TaskGenerateCPackedStruct::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    m_out->write("%s%s", (t->isSigned())?"u":"", m_int_t.c_str());
    m_width = t->getWidth();
}

void TaskGenerateCPackedStruct::visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) {
    DEBUG_ENTER("visitDataTypePackedStruct");
    m_out->write("%s", m_ctxt->nameMap()->getName(t).c_str());
//    m_bits += t->get

    DEBUG_LEAVE("visitDataTypePackedStruct");
}

void TaskGenerateCPackedStruct::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) {
    DEBUG_ENTER("visitTypeFieldPhy %s", f->name().c_str());
    m_out->write(m_out->ind());
    m_width = -1;
    f->getDataType()->accept(m_this);
    if (m_width > 0) {
        m_out->write(" %s:%d;\n", f->name().c_str(), m_width);
        m_bits += m_width;
    } else {
        m_out->write(" %s;\n", f->name().c_str());
    }
    DEBUG_LEAVE("visitTypeFieldPhy %s", f->name().c_str());
}

dmgr::IDebug *TaskGenerateCPackedStruct::m_dbg = 0;

}
}
}
