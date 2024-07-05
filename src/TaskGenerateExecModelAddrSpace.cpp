/*
 * TaskGenerateExecModelAddrSpace.cpp
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
#include "zsp/arl/dm/IDataTypeAddrSpaceC.h"
#include "zsp/arl/dm/IDataTypeAddrSpaceTransparentC.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelAddrSpace.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelAddrSpace::TaskGenerateExecModelAddrSpace(
    TaskGenerateExecModel       *gen,
    IOutput                     *out_h,
    IOutput                     *out_c) :
    m_gen(gen), m_out_h(out_h), m_out_c(out_c) {

}

TaskGenerateExecModelAddrSpace::~TaskGenerateExecModelAddrSpace() {

}

void TaskGenerateExecModelAddrSpace::generate(arl::dm::IDataTypeAddrSpaceC *t) {
    // TODO: should have access to trait
    m_out_h->println("typedef struct %s_s {",
        m_gen->getNameMap()->getName(t).c_str());
    m_out_h->inc_ind();
    m_out_h->println("zsp_rt_addr_space_t       aspace;");
    m_out_h->dec_ind();
    m_out_h->println("} %s_t;",
        m_gen->getNameMap()->getName(t).c_str());

    m_out_c->println("void %s__init(%s_t *actor, %s_t *this_p) {",
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());
    m_out_c->inc_ind();
    m_out_c->println("zsp_rt_addr_space_init(&actor->actor, &this_p->aspace, 0);");
    m_out_c->dec_ind();
    m_out_c->println("}");

}

}
}
}
