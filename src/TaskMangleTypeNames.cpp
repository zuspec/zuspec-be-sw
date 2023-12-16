/*
 * TaskMangleTypeNames.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskMangleTypeNames.h"


namespace zsp {
namespace be {
namespace sw {


TaskMangleTypeNames::TaskMangleTypeNames(
    dmgr::IDebugMgr             *dmgr,
    INameMap                    *name_m) : m_name_m(name_m) {
    DEBUG_INIT("TaskMangleTypeName", dmgr);
}

TaskMangleTypeNames::~TaskMangleTypeNames() {

}

void TaskMangleTypeNames::mangle(vsc::dm::IDataTypeStruct *t) {
    if (!m_name_m->hasName(t)) {
        t->accept(m_this);
    }
}

void TaskMangleTypeNames::visitDataTypeAction(arl::dm::IDataTypeAction *i) {
    std::string name = i->name();
    std::replace(name.begin(), name.end(), ':', '_');

    // Replace '::' -> '__'
    m_name_m->setName(i, name);
}

void TaskMangleTypeNames::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    std::string name = t->name();
    std::replace(name.begin(), name.end(), ':', '_');

    // Replace '::' -> '__'
    m_name_m->setName(t, name);
}

dmgr::IDebug     *TaskMangleTypeNames::m_dbg = 0;
}
}
}
