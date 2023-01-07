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
#include "TaskGenerateEmbCDataType.h"

using namespace zsp::arl::dm;

namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCDataType::TaskGenerateEmbCDataType(
    IOutput             *out,
    NameMap             *name_m) : m_out(out), m_name_m(name_m) {

}

TaskGenerateEmbCDataType::~TaskGenerateEmbCDataType() {

}

void TaskGenerateEmbCDataType::generate(vsc::dm::IDataType *type) {
    type->accept(m_this);
}

void TaskGenerateEmbCDataType::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {
    m_out->write("%s", m_name_m->getName(t).c_str());
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
    m_out->write("%s", m_name_m->getName(t).c_str());
}

}
}
}
