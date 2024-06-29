/*
 * TaskGenerateExecModelVarType.cpp
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
#include "TaskGenerateExecModelVarType.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelVarType::TaskGenerateExecModelVarType(
    TaskGenerateExecModel       *gen,
    IOutput                     *out,
    bool                        fparam) : m_gen(gen), m_out(out), m_fparam(fparam) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelVarType", gen->getDebugMgr());
}

TaskGenerateExecModelVarType::~TaskGenerateExecModelVarType() {

}

void TaskGenerateExecModelVarType::generate(vsc::dm::IDataType *t) {
    DEBUG_ENTER("generate");
    t->accept(m_this);
    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelVarType::visitDataTypeAction(arl::dm::IDataTypeAction *i) { }

void TaskGenerateExecModelVarType::visitDataTypeArray(vsc::dm::IDataTypeArray *t) { } 

void TaskGenerateExecModelVarType::visitDataTypeBool(vsc::dm::IDataTypeBool *t) {

}

void TaskGenerateExecModelVarType::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) { }

void TaskGenerateExecModelVarType::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) { }

void TaskGenerateExecModelVarType::visitDataTypeInt(vsc::dm::IDataTypeInt *t) { 
    DEBUG_ENTER("visitDataTypeInt");
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

    m_out->write("%s ", tname);

    DEBUG_LEAVE("visitDataTypeInt");
}

void TaskGenerateExecModelVarType::visitDataTypePtr(vsc::dm::IDataTypePtr *t) { }

void TaskGenerateExecModelVarType::visitDataTypeString(vsc::dm::IDataTypeString *t) { }

void TaskGenerateExecModelVarType::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) { 
    m_out->write("struct %s_s%s",
        m_gen->getNameMap()->getName(t).c_str(),
        (m_fparam)?" *":" ");
}

dmgr::IDebug *TaskGenerateExecModelVarType::m_dbg = 0;

}
}
}
