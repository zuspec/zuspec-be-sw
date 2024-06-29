/*
 * TaskGenerateExecModelStruct.cpp
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
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelStruct::TaskGenerateExecModelStruct(
    TaskGenerateExecModel   *gen,
    IOutput                 *out) : m_gen(gen), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelStruct", gen->getDebugMgr());
}

TaskGenerateExecModelStruct::~TaskGenerateExecModelStruct() {

}

void TaskGenerateExecModelStruct::generate(vsc::dm::IAccept *i) {
    DEBUG_ENTER("generate");
    m_out->println("typedef struct %s_s {", m_gen->getNameMap()->getName(i).c_str());
    m_out->inc_ind();
    m_depth = 0;
    m_ptr = 0;
    m_field = 0;
    m_field_m.clear();
    i->accept(m_this);
    m_out->dec_ind();
    m_out->println("} %s_t;", m_gen->getNameMap()->getName(i).c_str());
    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelStruct::visitDataTypeArray(vsc::dm::IDataTypeArray *t) {
    // Must handle this post-process

}

void TaskGenerateExecModelStruct::visitDataTypeBool(vsc::dm::IDataTypeBool *t) {
    m_out->write("zsp_rt_bool_t%s", (m_depth==1)?" ":"");
}

void TaskGenerateExecModelStruct::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {

}

void TaskGenerateExecModelStruct::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    const char *tname = 0;

    if (t->getByteSize() > 4) {
        tname = (t->isSigned())?"int64_t":"uint64_t";
    } else if (t->getByteSize() > 2) {
        tname = (t->isSigned())?"int32_t":"uint32_t";
    } else if (t->getByteSize() > 1) {
        tname = (t->isSigned())?"int16_t":"uint16_t";
    } else {
        tname = (t->isSigned())?"int8_t":"uint8_t";
    }

//    m_out->write("%s%s", tname, (m_depth==1)?" ":"");
    m_out->write("%s ", tname);
}

void TaskGenerateExecModelStruct::visitDataTypePtr(vsc::dm::IDataTypePtr *t) {
    m_ptr++;
    // TODO:
    m_ptr--;
}

void TaskGenerateExecModelStruct::visitDataTypeString(vsc::dm::IDataTypeString *t) {
    m_out->write("zsp_rt_string%s", (m_depth==1)?" ":"");
}

void TaskGenerateExecModelStruct::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct");
    if (m_depth == 0) {
        // We're processing the root type

        // Might benefit from a breadcrumb about inheritance

        // Setup to handle shadowed variables
        for (std::vector<vsc::dm::ITypeFieldUP>::const_reverse_iterator
            it=t->getFields().rbegin();
            it!=t->getFields().rend(); it++) {
            FieldM::iterator fit;
            
            if ((fit=m_field_m.find((*it)->name())) != m_field_m.end()) {
                fit->second++;
            } else {
                m_field_m.insert({(*it)->name(), 0});
            }
        }

        // Now, go generate the fields
        m_depth++;
        for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
            it=t->getFields().begin();
            it!=t->getFields().end(); it++) {
            (*it)->accept(m_this);
        }
        m_depth--;
    } else {
        m_out->write("struct %s_s%s",
            m_gen->getNameMap()->getName(t).c_str(),
            (m_depth==1)?" ":"");
    }

    DEBUG_LEAVE("visitDataTypeStruct");
}

void TaskGenerateExecModelStruct::visitDataTypeWrapper(vsc::dm::IDataTypeWrapper *t) {
    DEBUG_ENTER("visitDataTypeWrapper");
    t->getDataTypeVirt()->accept(m_this);
    DEBUG_LEAVE("visitDataTypeWrapper");
}

void TaskGenerateExecModelStruct::visitTypeField(vsc::dm::ITypeField *f) {
    DEBUG_ENTER("visitField");
    m_field = f;
    m_out->indent();
    // First print the datatype
    f->getDataType()->accept(m_this);

    FieldM::iterator fit = m_field_m.find(m_field->name());

    if (fit->second) {
        char tmp[64];
        sprintf(tmp, "%d", fit->second);

        m_gen->getNameMap()->setName(f, m_field->name() + "__" + tmp);
        m_out->write("%s__%d", 
            m_field->name().c_str(), 
            fit->second);
        fit->second--;
    } else {
        m_out->write("%s", m_field->name().c_str());
    }

    // TODO: if fixed-size array

    m_out->write(";\n");
    DEBUG_LEAVE("visitField");
}

void TaskGenerateExecModelStruct::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    DEBUG_ENTER("visitTypeFieldRef %s", f->name().c_str());
    m_field = f;
    m_out->indent();
    // First print the datatype
    m_depth++;
    f->getDataType()->accept(m_this);
    m_depth--;

    FieldM::iterator fit = m_field_m.find(m_field->name());

    if (fit->second) {
        char tmp[64];
        sprintf(tmp, "%d", fit->second);

        m_gen->getNameMap()->setName(f, m_field->name() + "__" + tmp);
        m_out->write(" *%s__%d", 
            m_field->name().c_str(), 
            fit->second);
        fit->second--;
    } else {
        m_out->write(" *%s", m_field->name().c_str());
    }

    // TODO: if fixed-size array

    m_out->write(";\n");
    DEBUG_LEAVE("visitTypeFieldRef");
}

void TaskGenerateExecModelStruct::visitTypeFieldRegGroup(arl::dm::ITypeFieldRegGroup *f) {
    DEBUG_ENTER("visitTypeFieldRegGroup");
    m_out->indent();
    m_depth++;
    f->getDataType()->accept(m_this);
    m_depth--;
    m_out->write(" *%s;\n", f->name().c_str());
    DEBUG_LEAVE("visitTypeFieldRegGroup");
}

dmgr::IDebug *TaskGenerateExecModelStruct::m_dbg = 0;

}
}
}
