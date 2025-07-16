/*
 * TaskGatherTypes.cpp
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
#include "TaskGatherTypes.h"


namespace zsp {
namespace be {
namespace sw {


TaskGatherTypes::TaskGatherTypes(IContext *ctxt) : m_ctxt(ctxt) {
    DEBUG_INIT("zsp::be::sw::TaskGatherTypes", ctxt->getDebugMgr());
}

TaskGatherTypes::~TaskGatherTypes() {

}

void TaskGatherTypes::gather(vsc::dm::IAccept *item) {
    DEBUG_ENTER("gather");
    item->accept(m_this);
    DEBUG_LEAVE("gather");
}

void TaskGatherTypes::visitDataTypeArlStruct(arl::dm::IDataTypeArlStruct *t) {
    DEBUG_ENTER("visitDataTypeArlStruct");
    if (m_types_s.find(t) == m_types_s.end()) {
        const std::string &name = t->name();

        DEBUG("name: %s", name.c_str());

        if (name.find("std_pkg::") == -1 
            && name.find("addr_reg_pkg::") == -1
            && name.find("executor_pkg::") == -1) {
            m_types_s.insert(t);
            m_types.push_back(t);
            arl::dm::VisitorBase::visitDataTypeArlStruct(t);
        }
    }
    DEBUG_LEAVE("visitDataTypeArlStruct");
}

void TaskGatherTypes::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());
    if (m_types_s.find(t) == m_types_s.end()) {
        const std::string &name = t->name();

        DEBUG("name: %s", name.c_str());

        if (name.find("std_pkg::") == -1 
            && name.find("addr_reg_pkg::") == -1
            && name.find("executor_pkg::") == -1) {
            m_types_s.insert(t);
            m_types.push_back(t);
            arl::dm::VisitorBase::visitDataTypeStruct(t);
        }
    }
    DEBUG_LEAVE("visitDataTypeStruct %s", t->name().c_str());
}

void TaskGatherTypes::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    if (f->name() != "comp") {
        f->getDataType()->accept(m_this);
    }
}

dmgr::IDebug *TaskGatherTypes::m_dbg = 0;

}
}
}
