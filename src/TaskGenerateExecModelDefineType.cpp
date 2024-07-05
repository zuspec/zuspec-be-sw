/*
 * TaskGenerateExecModelDefineType.cpp
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
#include "ITaskGenerateExecModelCustomGen.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelAction.h"
#include "TaskGenerateExecModelActivity.h"
#include "TaskGenerateExecModelAddrSpace.h"
#include "TaskGenerateExecModelComponent.h"
#include "TaskGenerateExecModelDefineType.h"
#include "TaskGenerateExecModelPackedStruct.h"
#include "TaskGenerateExecModelRegGroup.h"
#include "TaskGenerateExecModelStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelDefineType::TaskGenerateExecModelDefineType(
    TaskGenerateExecModel       *gen,
    IOutput                     *out_h,
    IOutput                     *out_c) : m_gen(gen), m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelDefineType", gen->getDebugMgr());
}

TaskGenerateExecModelDefineType::~TaskGenerateExecModelDefineType() {

}

void TaskGenerateExecModelDefineType::generate(vsc::dm::IDataType *item) {
    ITaskGenerateExecModelCustomGen *custom_gen = 
        dynamic_cast<ITaskGenerateExecModelCustomGen *>(item->getAssociatedData());
    if (custom_gen) {
        custom_gen->genDefinition(m_gen, m_out_h, m_out_c, item);
    } else {
        item->accept(m_this);
    }
}

void TaskGenerateExecModelDefineType::generate_dflt(vsc::dm::IDataType *item) {
    item->accept(m_this);
}

void TaskGenerateExecModelDefineType::visitDataTypeAction(arl::dm::IDataTypeAction *i) { 
    DEBUG_ENTER("visitDataTypeAction %s", i->name().c_str());
    TaskGenerateExecModelAction(m_gen).generate(i);
    DEBUG_LEAVE("visitDataTypeAction");
}

void TaskGenerateExecModelDefineType::visitDataTypeActivity(arl::dm::IDataTypeActivity *t) { 
    DEBUG_ENTER("visitDataTypeActivity");
    TaskGenerateExecModelActivity(m_gen).generate(t);
    DEBUG_LEAVE("visitDataTypeActivity");
}

void TaskGenerateExecModelDefineType::visitDataTypeAddrSpaceC(arl::dm::IDataTypeAddrSpaceC *t) {
    DEBUG_ENTER("visitDataTypeAddrSpaceC");
    TaskGenerateExecModelAddrSpace(m_gen, m_out_h, m_out_c).generate(t);
    DEBUG_LEAVE("visitDataTypeAddrSpaceC");
}

void TaskGenerateExecModelDefineType::visitDataTypeAddrSpaceTransparentC(arl::dm::IDataTypeAddrSpaceTransparentC *t) {
    DEBUG_ENTER("visitDataTypeAddrSpaceTransparentC");
    TaskGenerateExecModelAddrSpace(m_gen, m_out_h, m_out_c).generate(t);
    DEBUG_LEAVE("visitDataTypeAddrSpaceTransparentC");
}

void TaskGenerateExecModelDefineType::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) { 
    DEBUG_ENTER("visitDataTypeComponent");
    TaskGenerateExecModelComponent(m_gen).generate(t);
    DEBUG_LEAVE("visitDataTypeComponent");
}

void TaskGenerateExecModelDefineType::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) { }

void TaskGenerateExecModelDefineType::visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) {
    DEBUG_ENTER("visitDataTypePackedStruct");
    TaskGenerateExecModelPackedStruct(m_gen, m_out_h, m_out_c).generate(t);
    DEBUG_LEAVE("visitDataTypePackedStruct");
}

void TaskGenerateExecModelDefineType::visitDataTypeRegGroup(arl::dm::IDataTypeRegGroup *t) {
    DEBUG_ENTER("visitDataTypeRegGroup");
    TaskGenerateExecModelRegGroup(m_gen, m_out_h, m_out_c).generate(t);
    DEBUG_LEAVE("visitDataTypeRegGroup");
}

void TaskGenerateExecModelDefineType::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());
    TaskGenerateExecModelStruct(m_gen, m_out_h).generate(t);
    DEBUG_LEAVE("visitDataTypeStruct");
} 

dmgr::IDebug *TaskGenerateExecModelDefineType::m_dbg = 0;

}
}
}
