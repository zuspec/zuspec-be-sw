/*
 * TaskGatherRootActions.cpp
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
#include "TaskGatherRootActions.h"


namespace zsp {
namespace be {
namespace sw {


TaskGatherRootActions::TaskGatherRootActions(
    IContext                    *ctxt,
    arl::dm::IDataTypeComponent *pss_top) : m_ctxt(ctxt), m_pss_top(pss_top) {

}

TaskGatherRootActions::~TaskGatherRootActions() {

}

void TaskGatherRootActions::gather(std::vector<vsc::dm::IAccept *> &roots) {
    m_roots = &roots;
    m_roots->clear();

    m_pss_top->accept(this);
}

void TaskGatherRootActions::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    if (m_processed.find(t) == m_processed.end()) {
        m_processed.insert(t);
        for (auto it=t->getActionTypes().begin(); it!=t->getActionTypes().end(); it++) {
            (*it)->accept(this);
        }
        for (auto it=t->activities().begin(); it!=t->activities().end(); it++) {
            (*it)->accept(this);
        }
        for (auto it=t->getFields().begin(); it!=t->getFields().end(); it++) {
            (*it)->accept(this);
        }
        m_roots->push_back(t);
    }
}

void TaskGatherRootActions::visitDataTypeAction(arl::dm::IDataTypeAction *t) {
    if (m_processed.find(t) == m_processed.end()) {
        m_processed.insert(t);
        m_roots->push_back(t);
    }
}

void TaskGatherRootActions::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *t) {
    t->getDataType()->accept(this);
}

}
}
}
