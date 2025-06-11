/*
 * TaskGenerateActionAlloc.cpp
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
#include "TaskGenerateActionAlloc.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateActionAlloc::TaskGenerateActionAlloc(
        IContext                    *ctxt,
        TypeInfo                    *type_info,
        IOutput                     *out_h,
        IOutput                     *out_c) : 
        m_ctxt(ctxt), m_type_info(type_info), m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateActionAlloc", ctxt->getDebugMgr());
}

TaskGenerateActionAlloc::~TaskGenerateActionAlloc() {

}

void TaskGenerateActionAlloc::generate(arl::dm::IDataTypeAction *action) {
    DEBUG_ENTER("generate");

    m_out_c->println("void %s__alloc(%s_t *actor, %s_t *this_p) {",
        m_ctxt->nameMap()->getName(action).c_str(),
        "abc" /* m_gen->getActorName().c_str() */,
        m_ctxt->nameMap()->getName(action).c_str());
    m_out_c->inc_ind();
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=action->getFields().begin();
        it!=action->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_out_c->dec_ind();
    m_out_c->println("}");

    DEBUG_LEAVE("generate");
}

void TaskGenerateActionAlloc::visitTypeFieldAddrClaim(arl::dm::ITypeFieldAddrClaim *f) {
    DEBUG_ENTER("visitTypeFieldAddrClaim");
    // TODO: need to know 
    m_out_c->println("zsp_rt_alloc_claim(");
    m_out_c->inc_ind();
    m_out_c->println("&actor->actor,");
//    m_out_c->println("actor->aspace_insts[this_p->comp->__aspace[%d]],", 
//        m_gen->getTraitTypeId(f->getTraitType()));
    m_out_c->println("(zsp_rt_addr_claimspec_t *)&this_p->%s,", f->name().c_str());
    m_out_c->println("0,");
    m_out_c->println("0");
    m_out_c->dec_ind();
    m_out_c->println(");");
    DEBUG_LEAVE("visitTypeFieldAddrClaim");
}

void TaskGenerateActionAlloc::visitTypeFieldAddrClaimTransparent(arl::dm::ITypeFieldAddrClaimTransparent *f) {
    visitTypeFieldAddrClaim(f);
}

dmgr::IDebug *TaskGenerateActionAlloc::m_dbg = 0;

}
}
}
