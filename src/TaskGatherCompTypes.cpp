/*
 * TaskGatherCompTypes.cpp
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
#include "TaskGatherCompTypes.h"


namespace zsp {
namespace be {
namespace sw {


TaskGatherCompTypes::TaskGatherCompTypes(IContext *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("zsp::be::sw::TaskGatherCompTypes", ctxt->getDebugMgr());
}

TaskGatherCompTypes::~TaskGatherCompTypes() {

}

void TaskGatherCompTypes::gather(
        arl::dm::IDataTypeComponent                 *pss_top,
        std::vector<arl::dm::IDataTypeComponent *>  &comp_types) {
    DEBUG_ENTER("gather");
    m_comp_types = &comp_types;
    pss_top->accept(m_this);
    DEBUG_LEAVE("gather %d", comp_types.size());
}

void TaskGatherCompTypes::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent %s", t->name().c_str());
    if (m_processed.find(t) == m_processed.end()) {
        DEBUG("Adding...");
        m_processed.insert(t);
        m_comp_types->push_back(t);
        for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
            it=t->getFields().begin();
            it!=t->getFields().end(); it++) {
            (*it)->accept(m_this);
        }
    } else {
        DEBUG("Already processed");
    }
    DEBUG_LEAVE("visitDataTypeComponent %s", t->name().c_str());
}

void TaskGatherCompTypes::visitTypeField(vsc::dm::ITypeField *t) {
    t->getDataType()->accept(m_this);
}

dmgr::IDebug *TaskGatherCompTypes::m_dbg = 0;

}
}
}
