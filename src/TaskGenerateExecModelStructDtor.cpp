/*
 * TaskGenerateExecModelStructDtor.cpp
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
#include "TaskGenerateExecModelStructDtor.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelStructDtor::TaskGenerateExecModelStructDtor(
    TaskGenerateExecModel       *gen,
    IOutput                     *out_h,
    IOutput                     *out_c) : 
    m_dbg(0), m_gen(gen), m_out_h(out_h), m_out_c(out_c), m_field(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelStructDtor", gen->getDebugMgr());
}

TaskGenerateExecModelStructDtor::~TaskGenerateExecModelStructDtor() {

}

void TaskGenerateExecModelStructDtor::generate_enter(vsc::dm::IDataTypeStruct *t) {
    m_out_c->println("static void %s__dtor(%s_t *actor, %s_t *this_p) {", 
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());
    m_out_c->inc_ind();
}

void TaskGenerateExecModelStructDtor::generate(vsc::dm::IDataTypeStruct *t) {
    generate_enter(t);

    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }

    generate_leave(t);
}

void TaskGenerateExecModelStructDtor::generate_leave(vsc::dm::IDataTypeStruct *t) {
    m_out_c->dec_ind();
    m_out_c->println("}");
}

void TaskGenerateExecModelStructDtor::visitDataTypeAction(arl::dm::IDataTypeAction *t) { 
    DEBUG_ENTER("visitDataTypeAction");
    if (m_field) {
        m_out_c->println("if (this_p->%s) {", m_field->name().c_str());
        m_out_c->inc_ind();
        m_out_c->println("%s__dtor(actor, this_p->%s);",
            m_gen->getNameMap()->getName(t).c_str(),
            m_field->name().c_str());
        m_out_c->dec_ind();
        m_out_c->println("}");
    }
    DEBUG_LEAVE("visitDataTypeAction");
}

void TaskGenerateExecModelStructDtor::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) { 
    DEBUG_ENTER("visitDataTypeComponent");
    // No action
    DEBUG_LEAVE("visitDataTypeComponent");
}

void TaskGenerateExecModelStructDtor::visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) {
    DEBUG_ENTER("visitDataTypePackedStruct");
    // No action
    DEBUG_LEAVE("visitDataTypePackedStruct");
}

void TaskGenerateExecModelStructDtor::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct");

    // If this field is an address handle, then we decrement the storage
    if (t == m_gen->getAddrHandleT()) {
    } else {
        // Otherwise, we need to call the appropriate dtor
        m_out_c->println("%s__dtor(actor, &this_p->%s);",
            m_gen->getNameMap()->getName(t).c_str(),
            m_field->name().c_str());
    }

    DEBUG_LEAVE("visitDataTypeStruct");
}

void TaskGenerateExecModelStructDtor::visitDataTypeFlowObj(arl::dm::IDataTypeFlowObj *t) { }

void TaskGenerateExecModelStructDtor::visitTypeFieldAddrClaim(arl::dm::ITypeFieldAddrClaim *f) {
    DEBUG_ENTER("visitTypeFieldAddrClaim");
    m_out_c->println("zsp_rt_rc_dec((zsp_rt_rc_t *)this_p->%s.claim);", f->name().c_str());
    /*
    m_field = f;
    f->getDataType()->accept(m_this);
    m_field = 0;
     */
    DEBUG_LEAVE("visitTypeFieldAddrClaim");
}
    
void TaskGenerateExecModelStructDtor::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) { 
    m_field = f;
    f->getDataType()->accept(m_this);
    m_field = 0;
}

void TaskGenerateExecModelStructDtor::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) { 
    m_field = f;
    f->getDataType()->accept(m_this);
    m_field = 0;
}

}
}
}
