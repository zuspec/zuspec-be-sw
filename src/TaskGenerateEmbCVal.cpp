/*
 * TaskGenerateEmbCVal.cpp
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
#include "vsc/dm/impl/ValRefInt.h"
#include "vsc/dm/impl/ValRefStr.h"
#include "TaskGenerateEmbCVal.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCVal::TaskGenerateEmbCVal(IContext *ctxt) : m_ctxt(ctxt), m_out(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateEmbCVal", ctxt->getDebugMgr());
}

TaskGenerateEmbCVal::~TaskGenerateEmbCVal() {

}

void TaskGenerateEmbCVal::generate(
        IOutput                 *out,
        const vsc::dm::ValRef   &val) {
    DEBUG_ENTER("generate");
    m_out = out;
    m_val = val;
    val.type()->accept(m_this);
    DEBUG_LEAVE("generate");
}

void TaskGenerateEmbCVal::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    DEBUG_ENTER("visitDataTypeInt");
    vsc::dm::ValRefInt val_i(m_val);
    if (t->isSigned()) {
        m_out->write("%lld", val_i.get_val_s());
    } else {
        m_out->write("%llu", val_i.get_val_u());
    }
    DEBUG_LEAVE("visitDataTypeInt");
}

void TaskGenerateEmbCVal::visitDataTypeString(vsc::dm::IDataTypeString *t) {
    DEBUG_ENTER("visitDataTypeString");
    vsc::dm::ValRefStr val_s(m_val);
    m_out->write("\"%s\"", val_s.val());
    DEBUG_LEAVE("visitDataTypeString");
}

dmgr::IDebug *TaskGenerateEmbCVal::m_dbg = 0;

}
}
}
