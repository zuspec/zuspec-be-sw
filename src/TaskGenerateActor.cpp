/*
 * TaskGenerateActor.cpp
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
#include "TaskGenerateActor.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateActor::TaskGenerateActor(
    IContext    *ctxt, 
    IOutput     *out_h,
    IOutput     *out_c) : m_ctxt(ctxt), m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateActor", ctxt->getDebugMgr());
}

TaskGenerateActor::~TaskGenerateActor() {

}

void TaskGenerateActor::generate(
        arl::dm::IDataTypeComponent *comp_t,
        arl::dm::IDataTypeAction    *action_t) {
    DEBUG_ENTER("generate");

    std::string fullname;
    fullname = m_ctxt->nameMap()->getName(action_t);

    m_out_h->println("typedef struct %s_s {", fullname.c_str());
    m_out_h->inc_ind();
    m_out_h->println("zsp_actor(%s);", m_ctxt->nameMap()->getName(comp_t).c_str());
    m_out_h->dec_ind();
    m_out_h->println("} %s_t;", fullname.c_str());

//    my_actor_init(&actor, a=4, b=7)
    

    DEBUG_LEAVE("generate");
}

dmgr::IDebug *TaskGenerateActor::m_dbg = 0;

}
}
}
