/*
 * TaskBuildStaticCompTreeMap.cpp
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
#include "TaskBuildStaticCompTreeMap.h"


namespace zsp {
namespace be {
namespace sw {


TaskBuildStaticCompTreeMap::TaskBuildStaticCompTreeMap(dmgr::IDebugMgr *dmgr) {
    DEBUG_INIT("zsp::be::sw::TaskBuildStaticCompTreeMap", dmgr);
}

TaskBuildStaticCompTreeMap::~TaskBuildStaticCompTreeMap() {

}

TaskBuildStaticCompTreeMap::CompTreeM TaskBuildStaticCompTreeMap::build(arl::dm::IDataTypeComponent *comp_t) {
    DEBUG_ENTER("build %s", comp_t->name().c_str());
    m_num_comp = 0;

    CompData comp_data;
    comp_data.num_comp = 0;
    comp_data.sub_comp_m.insert({comp_t, {comp_data.num_comp++}});
    m_comp_s.push_back(&comp_data);
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=comp_t->getFields().begin();
        it!=comp_t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_comp_s.pop_back();
    m_comp_data.insert({comp_t, comp_data});

    CompTreeM ret;
    for (std::map<arl::dm::IDataTypeComponent *,CompData>::const_iterator
        it=m_comp_data.begin();
        it!=m_comp_data.end(); it++) {
        ret.insert({it->first, it->second.sub_comp_m});
        if (DEBUG_EN) {
            DEBUG("Comp: %s", it->first->name().c_str());
            for (std::map<arl::dm::IDataTypeComponent *, std::vector<int32_t>>::const_iterator
                sub_it=it->second.sub_comp_m.begin();
                sub_it!=it->second.sub_comp_m.end(); sub_it++) {
                DEBUG("  SubComp: %s", sub_it->first->name().c_str());
                for (std::vector<int32_t>::const_iterator
                    inst_it=sub_it->second.begin();
                    inst_it!=sub_it->second.end(); inst_it++) {
                    DEBUG("    Offset: %d", *inst_it);
                }
            }
        }
    }
    DEBUG_LEAVE("build %s", comp_t->name().c_str());
    return ret;
}

void TaskBuildStaticCompTreeMap::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent %s", t->name().c_str());
    std::map<arl::dm::IDataTypeComponent *, CompData>::iterator it;

    if ((it=m_comp_data.find(t)) == m_comp_data.end()) {
        // 
        CompData comp_data;
        comp_data.num_comp = 0;
        comp_data.sub_comp_m.insert({t, {comp_data.num_comp++}});
        m_comp_s.push_back(&comp_data);
        for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
            it=t->getFields().begin();
            it!=t->getFields().end(); it++) {
            (*it)->accept(m_this);
        }
        m_comp_s.pop_back();
        it = m_comp_data.insert({t, comp_data}).first;
    } else {
//        it->second.sub_comp_m.find(t)->second.push_back(m_num_comp++);
    }

    // Fold info about this component type into the scopes currently being processed
    // Iterate through entries in the component-type map
    // and reflect them up the tree 
    CompData *last = m_comp_s.back();
    for (std::map<arl::dm::IDataTypeComponent *, std::vector<int32_t>>::const_iterator
        sc_it=it->second.sub_comp_m.begin();
        sc_it!=it->second.sub_comp_m.end(); sc_it++) {
        std::map<arl::dm::IDataTypeComponent *, std::vector<int32_t>>::iterator ct_it;

        if ((ct_it=last->sub_comp_m.find(sc_it->first)) == last->sub_comp_m.end()) {
            // No entry, yet, for this type
            ct_it = last->sub_comp_m.insert({sc_it->first, std::vector<int32_t>()}).first;
        }

        for (std::vector<int32_t>::const_iterator
            id_it=sc_it->second.begin();
            id_it!=sc_it->second.end(); id_it++) {
            DEBUG("Add instance of %s: offset=%d inst_id=%d",
                sc_it->first->name().c_str(),
                *id_it,
                (last->num_comp+*id_it));
            ct_it->second.push_back(last->num_comp+*id_it);
        }
    }

    DEBUG("Adjust num_comp %d -> %d",
        last->num_comp, (last->num_comp+it->second.num_comp));
    last->num_comp += it->second.num_comp;

    DEBUG_LEAVE("visitDataTypeComponent %s", t->name().c_str());
}

dmgr::IDebug *TaskBuildStaticCompTreeMap::m_dbg = 0;

}
}
}
