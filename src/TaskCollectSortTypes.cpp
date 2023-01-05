/*
 * TaskCollectSortTypes.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskCollectSortTypes.h"


namespace zsp {
namespace be {
namespace sw {


TaskCollectSortTypes::TaskCollectSortTypes(dmgr::IDebugMgr *dmgr) {
    fprintf(stdout, "TaskCollect: dmgr=%p\n", dmgr);
    DEBUG_INIT("TaskCollectSortTypes", dmgr);
}

TaskCollectSortTypes::~TaskCollectSortTypes() {

}

void TaskCollectSortTypes::collect(vsc::dm::IDataTypeStruct *root) {
    DEBUG_ENTER("collect");
    root->accept(m_this);
    DEBUG_LEAVE("collect");
}

void TaskCollectSortTypes::visitDataTypeComponent(
        arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent %s", t->name().c_str());
    enterType(t);
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    leaveType(); 
    DEBUG_LEAVE("visitDataTypeComponent %s", t->name().c_str());
}

void TaskCollectSortTypes::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeSTruct %s", t->name().c_str());
    enterType(t);
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    leaveType(); 
    DEBUG_LEAVE("visitDataTypeSTruct %s", t->name().c_str());
}

void TaskCollectSortTypes::visitTypeField(vsc::dm::ITypeField *f) {
    DEBUG_ENTER("visitTypeField %s", f->name().c_str());
    f->getDataType()->accept(m_this);
    DEBUG_LEAVE("visitTypeField %s", f->name().c_str());
}

void TaskCollectSortTypes::sort(std::vector<vsc::dm::IDataTypeStruct *> &types) {
    std::vector<uint32_t> indegree(m_edges.size(), 0);

    for (uint32_t i=0; i<m_edges.size(); i++) {
        for (std::set<uint32_t>::const_iterator
            it=m_edges.at(i).begin();
            it!=m_edges.at(i).end(); it++) {
            indegree.at(*it) += 1;
        }
    }

    // First, find roots -- nodes without dependencies
    std::vector<uint32_t> roots;
    for (uint32_t i=0; i<m_edges.size(); i++) {
        if (indegree.at(i) == 0) {
            roots.push_back(i);
        }
    }

    uint32_t visited_cnt = 0;
    std::vector<uint32_t> sorted;

    while (roots.size()) {
        uint32_t node = roots.front();
        roots.erase(roots.begin());

        sorted.push_back(node);
        types.push_back(m_type_l.at(node));

        // Adjust dependencies on the node that we just added
        for (std::set<uint32_t>::const_iterator
            it=m_edges.at(node).begin();
            it!=m_edges.at(node).end(); it++) {
            if (indegree.at(*it)) {
                indegree.at(*it) -= 1;

                if (indegree.at(*it) == 0) {
                    roots.push_back(*it);
                }
            }
        }
    }
}

void TaskCollectSortTypes::enterType(vsc::dm::IDataTypeStruct *t) {
    std::map<vsc::dm::IDataTypeStruct *, int32_t>::iterator it;

    if ((it=m_type_m.find(t)) == m_type_m.end()) {
        it = m_type_m.insert({t, m_type_l.size()}).first;
        m_type_l.push_back(t);

        // Edge U -> V: U comes before V
        // tid must come before parent_tid
        m_edges.push_back({});
    }

    if (m_type_s.size() > 0) {
        m_edges.at(it->second).insert(m_type_s.back());
    }

    m_type_s.push_back(it->second);
}

void TaskCollectSortTypes::leaveType() {
    m_type_s.pop_back();
}

dmgr::IDebug *TaskCollectSortTypes::m_dbg = 0;

}
}
}
