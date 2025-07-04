/*
 * NameMap.cpp
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
#include <algorithm>
#include "NameMap.h"


namespace zsp {
namespace be {
namespace sw {


NameMap::NameMap() {
    m_name_m_s.push_back(KindMUP(new KindM()));
}

NameMap::~NameMap() {

}

void NameMap::push() {
    m_name_m_s.push_back(KindMUP(new KindM()));
}

void NameMap::pop() {
    m_name_m_s.pop_back();
}

void NameMap::setName(
    vsc::dm::IAccept    *type, 
    const std::string   &name,
    INameMap::Kind      kind) {
    KindM::iterator kind_it = m_name_m_s.back()->find(kind);
    NameM::iterator name_it;

    if (kind_it == m_name_m_s.back()->end()) {
        kind_it = m_name_m_s.back()->insert({kind, NameM()}).first;
    }
    name_it = kind_it->second.find(type);

    if (name_it != kind_it->second.end()) {
        // Erase old version
        kind_it->second.erase(name_it);
    }

    kind_it->second.insert({type, name});
}

bool NameMap::hasName(
        vsc::dm::IAccept    *type,
        Kind                kind) {
    KindM::iterator kind_it;
    
    for (std::vector<KindMUP>::const_reverse_iterator
        it=m_name_m_s.rbegin();
        it!=m_name_m_s.rend(); it++) {
        kind_it = (*it)->find(kind);

        if (kind_it != (*it)->end()) {
            NameM::iterator name_it = kind_it->second.find(type);

            if (name_it != kind_it->second.end()) {
                return true;
            }
        }
    }

    return false;
}

std::string NameMap::getName(
    vsc::dm::IAccept    *type,
    INameMap::Kind      kind) {
    std::string ret;

    // First search
    for (std::vector<KindMUP>::const_reverse_iterator
        it=m_name_m_s.rbegin();
        it!=m_name_m_s.rend(); it++) {
        KindM::iterator kind_it = (*it)->find(kind);
        NameM::iterator name_it;

        if (kind_it != (*it)->end()) {
            name_it = kind_it->second.find(type);

            if (name_it != kind_it->second.end()) {
                ret = name_it->second;
                break;
            }
        }
    }

    if (ret == "") {
        KindM::iterator kind_it = m_name_m_s.back()->find(kind);
        NameM::iterator name_it;
        if (kind_it == m_name_m_s.back()->end()) {
            kind_it = m_name_m_s.back()->insert({kind, NameM()}).first;
        }

        // Go compute the name
        m_name.clear();
        m_kind = kind;
        type->accept(m_this);
        std::replace(m_name.begin(), m_name.end(), ':', '_');
        name_it = kind_it->second.insert({type, m_name}).first;

        ret = name_it->second;
    }

    return ret;
}

void NameMap::visitDataTypeAction(arl::dm::IDataTypeAction *t) {
    m_name = t->name();
}

void NameMap::visitDataTypeAddrSpaceTransparentC(arl::dm::IDataTypeAddrSpaceTransparentC *t) {
    m_name = t->name();
}

void NameMap::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    m_name = t->name();
}

void NameMap::visitDataTypeFlowObj(arl::dm::IDataTypeFlowObj *t) {
    m_name = t->name();
}

void NameMap::visitDataTypeActivity(arl::dm::IDataTypeActivity *t) {
    char tmp[128];
    sprintf(tmp, "_%08p", t);
    m_name = "activity";
    m_name += tmp;
}

void NameMap::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) {
    m_name = t->name();
}

void NameMap::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    m_name = t->name();
}

void NameMap::visitDataTypeWrapper(vsc::dm::IDataTypeWrapper *t) {
    t->getDataTypeVirt()->accept(m_this);
}

void NameMap::visitTypeField(vsc::dm::ITypeField *t) {
    m_name = t->name();
}

}
}
}
