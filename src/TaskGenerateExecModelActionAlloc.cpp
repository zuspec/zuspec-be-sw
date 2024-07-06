/*
 * TaskGenerateExecModelActionAlloc.cpp
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
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelActionAlloc.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelActionAlloc::TaskGenerateExecModelActionAlloc(
        TaskGenerateExecModel       *gen,
        IOutput                     *out) : m_gen(gen), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelActionAlloc", gen->getDebugMgr());
}

TaskGenerateExecModelActionAlloc::~TaskGenerateExecModelActionAlloc() {

}

void TaskGenerateExecModelActionAlloc::generate(arl::dm::IDataTypeAction *action) {
    DEBUG_ENTER("generate");

    m_out->println("void %s__alloc(%s_t *actor, %s_t *this_p) {",
        m_gen->getNameMap()->getName(action).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(action).c_str());
    m_out->inc_ind();
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=action->getFields().begin();
        it!=action->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_out->dec_ind();
    m_out->println("}");

    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelActionAlloc::visitTypeFieldAddrClaim(arl::dm::ITypeFieldAddrClaim *f) {
    DEBUG_ENTER("visitTypeFieldAddrClaim");
    // TODO: need to know 
    m_out->println("zsp_rt_alloc_claim(");
    m_out->inc_ind();
    m_out->println("&actor->actor,");
    m_out->println("this_p->comp->%s_aspace,",
        m_gen->getNameMap()->getName(f->getTraitType()).c_str());
    m_out->println("this_p->%s.claim,", f->name().c_str());
    m_out->println("0,");
    m_out->println("0");
    m_out->dec_ind();
    m_out->println(");");
    DEBUG_LEAVE("visitTypeFieldAddrClaim");
}

void TaskGenerateExecModelActionAlloc::visitTypeFieldAddrClaimTransparent(arl::dm::ITypeFieldAddrClaimTransparent *f) {
    visitTypeFieldAddrClaim(f);
}

dmgr::IDebug *TaskGenerateExecModelActionAlloc::m_dbg = 0;

}
}
}
