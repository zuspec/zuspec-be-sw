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
#include "NameMap.h"


namespace zsp {
namespace be {
namespace sw {


NameMap::NameMap() {

}

NameMap::~NameMap() {

}

void NameMap::setName(vsc::dm::IDataType *type, const std::string &name) {
    m_type_m.insert({type, name});
}

void NameMap::setName(arl::dm::IDataTypeFunction *func, const std::string &name) {
    m_func_m.insert({func, name});
}

const std::string &NameMap::getName(vsc::dm::IDataType *type) {
    std::unordered_map<vsc::dm::IDataType *,std::string>::const_iterator it;
    
    if ((it=m_type_m.find(type)) != m_type_m.end()) {
        return it->second;
    } else {
        m_name.clear();
        type->accept(m_this);
        return m_name;
    }
}

const std::string &NameMap::getName(arl::dm::IDataTypeFunction *func) {
    std::unordered_map<arl::dm::IDataTypeFunction*,std::string>::const_iterator it;

    if ((it=m_func_m.find(func)) != m_func_m.end()) {
        return it->second;
    } else {
        m_name.clear();
        func->accept(m_this);
        return m_name;
    }
}

void NameMap::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) {
    m_name = t->name();
}

}
}
}
