/*
 * TaskGenerateExprVal.cpp
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
#include "vsc/dm/ITypeExprVal.h"
#include "vsc/dm/impl/ValRefArr.h"
#include "vsc/dm/impl/ValRefBool.h"
#include "vsc/dm/impl/ValRefInt.h"
#include "vsc/dm/impl/ValRefPtr.h"
#include "vsc/dm/impl/ValRefStr.h"
#include "vsc/dm/impl/ValRefStruct.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExprVal.h"


namespace zsp {
namespace be {
namespace sw {

TaskGenerateExprVal::TaskGenerateExprVal(
        IContext       *ctxt,
        IOutput        *out) : m_ctxt(ctxt), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExprVal", ctxt->getDebugMgr());
}

TaskGenerateExprVal::TaskGenerateExprVal(
        TaskGenerateExecModel       *gen,
        IOutput                     *out) : m_ctxt(0), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExprVal", gen->getDebugMgr());
}

TaskGenerateExprVal::~TaskGenerateExprVal() {

}

void TaskGenerateExprVal::generate(vsc::dm::ITypeExprVal *e) {
    DEBUG_ENTER("generate");
    m_val = e->val();
    e->type()->accept(m_this);
    DEBUG_LEAVE("generate");
}

void TaskGenerateExprVal::visitDataTypeArray(vsc::dm::IDataTypeArray *t) { 
    DEBUG_ENTER("visitDataTypeArray");
    DEBUG("TODO: visitDataTypeArray");
    DEBUG_LEAVE("visitDataTypeArray");
}

void TaskGenerateExprVal::visitDataTypeBool(vsc::dm::IDataTypeBool *t) { 
    DEBUG_ENTER("visitDataTypeBool");
    vsc::dm::ValRefBool vb(m_val);
    m_out->write("%s", vb.get_val()?"true":"false");
    DEBUG_LEAVE("visitDataTypeBool");
}

void TaskGenerateExprVal::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) { 
    DEBUG_ENTER("visitDataTypeEnum");
    DEBUG("TODO: visitDataTypeEnum");
    DEBUG_LEAVE("visitDataTypeEnum");
}

void TaskGenerateExprVal::visitDataTypeInt(vsc::dm::IDataTypeInt *t) { 
    DEBUG_ENTER("visitDataTypeInt");
    vsc::dm::ValRefInt vi(m_val);
    if (t->isSigned()) {
        m_out->write("%lld", vi.get_val_s());
    } else {
        m_out->write("0x%llx", vi.get_val_u());
    }
    DEBUG_LEAVE("visitDataTypeInt");
}

void TaskGenerateExprVal::visitDataTypePtr(vsc::dm::IDataTypePtr *t) { 
    DEBUG_ENTER("visitDataTypePtr");
    DEBUG("TODO: visitDataTypePtr");
    DEBUG_LEAVE("visitDataTypePtr");
}

void TaskGenerateExprVal::visitDataTypeString(vsc::dm::IDataTypeString *t) { 
    DEBUG_ENTER("visitDataTypeString");
    vsc::dm::ValRefStr vs(m_val);
    m_out->write("\"%s\"", vs.val());
    DEBUG_LEAVE("visitDataTypeString");
}

dmgr::IDebug *TaskGenerateExprVal::m_dbg = 0;

}
}
}
