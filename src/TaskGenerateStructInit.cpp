/*
 * TaskGenerateStructInit.cpp
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
#include "TaskGenerateStructInit.h"
#include "TaskGenerateExprNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateStructInit::TaskGenerateStructInit(
    IContext                *ctxt,
    IOutput                 *out_h,
    IOutput                 *out_c) : 
        m_dbg(0), m_ctxt(ctxt), m_depth(0), m_is_ref(false), 
        m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateStructInit", ctxt->getDebugMgr());
}

TaskGenerateStructInit::~TaskGenerateStructInit() {

}

void TaskGenerateStructInit::generate_prefix(vsc::dm::IDataTypeStruct *i) {
    m_out_h->println("void %s__init(struct zsp_actor_s *actor, struct %s_s *this_p);",
        m_ctxt->nameMap()->getName(i).c_str(),
        m_ctxt->nameMap()->getName(i).c_str());

    m_out_c->println("void %s__init(zsp_actor_t *actor, struct %s_s *this_p) {",
        m_ctxt->nameMap()->getName(i).c_str(),
        m_ctxt->nameMap()->getName(i).c_str());
    m_out_c->inc_ind();
}

void TaskGenerateStructInit::generate_core(vsc::dm::IDataTypeStruct *i) {
    m_out_c->println("((zsp_object_t *)this_p)->type = (zsp_object_type_t *)%s__type();",
        m_ctxt->nameMap()->getName(i).c_str());
}

void TaskGenerateStructInit::generate(vsc::dm::IDataTypeStruct *i) {
    m_depth = 0;
    generate_prefix(i);

    generate_core(i);

    m_depth++;
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=i->getFields().begin();
        it!=i->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_depth--;

    generate_suffix(i);
}

void TaskGenerateStructInit::generate_suffix(vsc::dm::IDataTypeStruct *i) {
    m_out_c->dec_ind();
    m_out_c->println("}");
}

void TaskGenerateStructInit::visitDataTypeAddrClaim(arl::dm::IDataTypeAddrClaim *t) {
    DEBUG_ENTER("visitDataTypeAddrClaim");
    // if (m_depth) {
    //     m_out_c->println("this_p->%s.claim = zsp_rt_addr_claim_new(&actor->actor);", 
    //         m_ctxt->nameMap()->getName(m_field).c_str());
    // }
    DEBUG_LEAVE("visitDataTypeAddrClaim");
}

void TaskGenerateStructInit::visitDataTypeArray(vsc::dm::IDataTypeArray *t) {}

void TaskGenerateStructInit::visitDataTypeBool(vsc::dm::IDataTypeBool *t) {

}

void TaskGenerateStructInit::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {}

void TaskGenerateStructInit::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    if (m_depth) {
        vsc::dm::ITypeFieldPhy *f = dynamic_cast<vsc::dm::ITypeFieldPhy *>(m_field);
        m_out_c->indent();
        m_out_c->write("this_p->%s = ", m_ctxt->nameMap()->getName(m_field).c_str());
        if (f->getInit()) {
            TaskGenerateExprNB(m_ctxt, 0, m_out_c).generate(f->getInit());
        } else {
            m_out_c->write("0");
        }
        m_out_c->write(";\n");
    }
}

void TaskGenerateStructInit::visitDataTypePtr(vsc::dm::IDataTypePtr *t) {}

void TaskGenerateStructInit::visitDataTypeString(vsc::dm::IDataTypeString *t) {}

void TaskGenerateStructInit::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct");
    if (m_depth) {
        if (!m_is_ref) {
            m_out_c->println("%s__init(actor, &this_p->%s);",
                m_ctxt->nameMap()->getName(t).c_str(),
                m_ctxt->nameMap()->getName(m_field).c_str(),
                m_ctxt->nameMap()->getName(t).c_str());
        }
    }
    DEBUG_LEAVE("visitDataTypeStruct");
}

void TaskGenerateStructInit::visitTypeField(vsc::dm::ITypeField *f) {
    DEBUG_ENTER("visitTypeField %s", f->name().c_str());
    m_field = f;
    f->getDataType()->accept(m_this);
    DEBUG_LEAVE("visitTypeField %s", f->name().c_str());
}

void TaskGenerateStructInit::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) {
    DEBUG_ENTER("visitTypeFieldPhy %s", f->name().c_str());
    m_field = f;
    m_is_ref = false;
    f->getDataType()->accept(m_this);
    DEBUG_LEAVE("visitTypeFieldPhy %s", f->name().c_str());
}

void TaskGenerateStructInit::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    DEBUG_ENTER("visitTypeFieldRef %s", f->name().c_str());
    m_field = f;
    m_is_ref = true;
    f->getDataType()->accept(m_this);
    DEBUG_LEAVE("visitTypeFieldRef %s", f->name().c_str());
}

void TaskGenerateStructInit::visitTypeFieldRegGroup(arl::dm::ITypeFieldRegGroup *f) {
    DEBUG_ENTER("visitTypeFieldRegGroup");
    DEBUG("TODO: visitTypeFieldRegGroup");
    DEBUG_LEAVE("visitTypeFieldRegGroup");
}


}
}
}
