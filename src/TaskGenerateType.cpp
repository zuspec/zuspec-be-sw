/*
 * TaskGenerateType.cpp
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
#include "TaskGenerateType.h"
#include <algorithm>
#include "dmgr/impl/DebugMacros.h"
#include "ITaskGenerateExecModelCustomGen.h"
#include "NameMap.h"
#include "Output.h"
#include "TaskBuildTypeCollection.h"
#include "TaskBuildTypeInfo.h"
#include "TaskGenerateExecModelAddrHandle.h"
#include "TaskGenerateExecModelCoreMethodCall.h"
#include "TaskGenerateExecModelMemRwCall.h"
#include "TaskGenerateExecModelRegRwCall.h"
#include "TaskGenerateExecModelAction.h"
#include "TaskGenerateExecModelActivity.h"
#include "TaskGenerateComp.h"
#include "TaskGenerateExecModelDefineType.h"
#include "TaskGenerateExecModelFwdDecl.h"
#include "TaskGenerateStruct.h"
#include "TypeCollection.h"




namespace zsp {
namespace be {
namespace sw {


TaskGenerateType::TaskGenerateType(
        IContext                 *ctxt,
        std::ostream             *out_c,
        std::ostream             *out_h) :
        m_ctxt(ctxt),
        m_out_c(new Output(out_c, false)),
        m_out_h(new Output(out_h, false)) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateType", ctxt->getDebugMgr());
}

TaskGenerateType::~TaskGenerateType() {

}

void TaskGenerateType::generate(vsc::dm::IDataTypeStruct *type_t) {
    type_t->accept(this);
    m_out_c->println("// Comment");
}

void TaskGenerateType::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent");
    TypeInfoUP type_info = TypeInfoUP(TaskBuildTypeInfo(m_ctxt).build(t));
    TaskGenerateComp(m_ctxt, type_info.get(), m_out_c.get(), m_out_h.get()).generate(t);
    DEBUG_LEAVE("visitDataTypeComponent");
}

void TaskGenerateType::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct");
    TypeInfoUP type_info = TypeInfoUP(TaskBuildTypeInfo(m_ctxt).build(t));
    TaskGenerateStruct(m_ctxt, type_info.get(), m_out_c.get(), m_out_h.get()).generate(t);
    DEBUG_LEAVE("visitDataTypeStruct");
}

void TaskGenerateType::visitDataTypeArlStruct(arl::dm::IDataTypeArlStruct *t) {
    DEBUG_ENTER("visitDataTypeArlStruct");
    visitDataTypeStruct(t);
    DEBUG_LEAVE("visitDataTypeArlStruct");
}

dmgr::IDebug *TaskGenerateType::m_dbg = 0;

}
}
}
