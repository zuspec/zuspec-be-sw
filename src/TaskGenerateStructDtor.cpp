/*
 * TaskGenerateStructDtor.cpp
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
#include "TaskGenerateStructDtor.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateStructDtor::TaskGenerateStructDtor(
    IContext       *ctxt,
    IOutput        *out):
    m_dbg(0), m_ctxt(ctxt), m_out(out), m_field(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateStructDtor", ctxt->getDebugMgr());
}

TaskGenerateStructDtor::~TaskGenerateStructDtor() {

}

void TaskGenerateStructDtor::generate_enter(vsc::dm::IDataTypeStruct *t) {
    m_out->println("static void %s__dtor(struct zsp_actor_s *actor, %s_t *this_p) {", 
        m_ctxt->nameMap()->getName(t).c_str(),
        m_ctxt->nameMap()->getName(t).c_str());
    m_out->inc_ind();
    m_out->println("%s__type_t *this_t = %s__type();", 
        m_ctxt->nameMap()->getName(t).c_str(),
        m_ctxt->nameMap()->getName(t).c_str());

    if (t->getSuper()) {
        m_out->println(
            "((zsp_object_type_t *)this_t)->dtor(actor, (zsp_object_t *)this_p);");
    }
}

void TaskGenerateStructDtor::generate(vsc::dm::IDataTypeStruct *t) {
    generate_enter(t);

    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }

    generate_leave(t);
}

void TaskGenerateStructDtor::generate_leave(vsc::dm::IDataTypeStruct *t) {
    m_out->dec_ind();
    m_out->println("}");
}

void TaskGenerateStructDtor::visitDataTypeAction(arl::dm::IDataTypeAction *t) { 
    DEBUG_ENTER("visitDataTypeAction");
    if (m_field) {
        m_out->println("if (this_p->%s) {", m_field->name().c_str());
        m_out->inc_ind();
        m_out->println("%s__dtor(actor, this_p->%s);",
            m_ctxt->nameMap()->getName(t).c_str(),
            m_field->name().c_str());
        m_out->dec_ind();
        m_out->println("}");
    }
    DEBUG_LEAVE("visitDataTypeAction");
}

void TaskGenerateStructDtor::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) { 
    DEBUG_ENTER("visitDataTypeComponent");
    // No action
    DEBUG_LEAVE("visitDataTypeComponent");
}

void TaskGenerateStructDtor::visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) {
    DEBUG_ENTER("visitDataTypePackedStruct");
    // No action
    DEBUG_LEAVE("visitDataTypePackedStruct");
}

void TaskGenerateStructDtor::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct");

    // If this field is an address handle, then we decrement the storage
    // if (t == m_gen->getAddrHandleT()) {
    // } else {
    //     // Otherwise, we need to call the appropriate dtor
    //     m_out->println("%s__dtor(actor, &this_p->%s);",
    //         m_gen->getNameMap()->getName(t).c_str(),
    //         m_field->name().c_str());
    // }

    DEBUG_LEAVE("visitDataTypeStruct");
}

void TaskGenerateStructDtor::visitDataTypeFlowObj(arl::dm::IDataTypeFlowObj *t) { }

void TaskGenerateStructDtor::visitTypeFieldAddrClaim(arl::dm::ITypeFieldAddrClaim *f) {
    DEBUG_ENTER("visitTypeFieldAddrClaim");
    m_out->println("zsp_rt_rc_dec((zsp_rt_rc_t *)this_p->%s.claim);", f->name().c_str());
    /*
    m_field = f;
    f->getDataType()->accept(m_this);
    m_field = 0;
     */
    DEBUG_LEAVE("visitTypeFieldAddrClaim");
}
    
void TaskGenerateStructDtor::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) { 
    m_field = f;
    f->getDataType()->accept(m_this);
    m_field = 0;
}

void TaskGenerateStructDtor::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) { 
    m_field = f;
    f->getDataType()->accept(m_this);
    m_field = 0;
}

}
}
}
