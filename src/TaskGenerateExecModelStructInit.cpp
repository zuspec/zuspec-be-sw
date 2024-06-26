/*
 * TaskGenerateExecModelStructInit.cpp
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
#include "TaskGenerateExecModelStructInit.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelStructInit::TaskGenerateExecModelStructInit(
    TaskGenerateExecModel   *gen) : m_dbg(0), m_gen(gen) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelStructInit", gen->getDebugMgr());
    m_out_c = gen->getOutC();
}

TaskGenerateExecModelStructInit::~TaskGenerateExecModelStructInit() {

}

void TaskGenerateExecModelStructInit::generate(vsc::dm::IAccept *i) {
    m_depth = 0;
    i->accept(m_this);
}

void TaskGenerateExecModelStructInit::visitDataTypeArray(vsc::dm::IDataTypeArray *t) {}

void TaskGenerateExecModelStructInit::visitDataTypeBool(vsc::dm::IDataTypeBool *t) {

}

void TaskGenerateExecModelStructInit::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {}

void TaskGenerateExecModelStructInit::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    if (m_depth) {
        m_out_c->println("this_p->%s = 0;", m_gen->getNameMap()->getName(m_field).c_str());
    }
}

void TaskGenerateExecModelStructInit::visitDataTypePtr(vsc::dm::IDataTypePtr *t) {}

void TaskGenerateExecModelStructInit::visitDataTypeString(vsc::dm::IDataTypeString *t) {}

void TaskGenerateExecModelStructInit::visitTypeField(vsc::dm::ITypeField *f) {
    m_field = f;
    f->getDataType()->accept(m_this);
}


}
}
}
