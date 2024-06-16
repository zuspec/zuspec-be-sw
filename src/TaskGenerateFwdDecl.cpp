/*
 * TaskGenerateFwdDecl.cpp
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
#include "zsp/be/sw/INameMap.h"
#include "TaskGenerateFwdDecl.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateFwdDecl::TaskGenerateFwdDecl(
    dmgr::IDebugMgr     *dmgr,
    INameMap            *name_m,
    IOutput             *out) : m_out(out), m_name_m(name_m) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateFwdDecl", dmgr);
}

TaskGenerateFwdDecl::~TaskGenerateFwdDecl() {

}

void TaskGenerateFwdDecl::generate(vsc::dm::IAccept *item) {
    item->accept(m_this);
}

void TaskGenerateFwdDecl::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent");
    m_out->println("struct %s_s;", m_name_m->getName(t).c_str());
    DEBUG_LEAVE("visitDataTypeComponent");
}

dmgr::IDebug *TaskGenerateFwdDecl::m_dbg = 0;

}
}
}
