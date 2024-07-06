/*
 * TaskGenerateExecModelStructInit.cpp
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
#include "TaskGenerateExecModelStructInit.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelStructInit::TaskGenerateExecModelStructInit(
    TaskGenerateExecModel   *gen) : m_dbg(0), m_gen(gen) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelStructInit", gen->getDebugMgr());
    m_out_c = gen->getOutC();
}

TaskGenerateExecModelStructInit::~TaskGenerateExecModelStructInit() {

}

void TaskGenerateExecModelStructInit::generate_prefix(vsc::dm::IDataTypeStruct *i) {
    m_gen->getOutC()->println("void %s__init(struct %s_s *actor, struct %s_s *this_p) {",
        m_gen->getNameMap()->getName(i).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(i).c_str());
    m_gen->getOutC()->inc_ind();
}

void TaskGenerateExecModelStructInit::generate(vsc::dm::IDataTypeStruct *i) {
    m_depth = 0;
    generate_prefix(i);

    m_depth++;
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=i->getFields().begin();
        it!=i->getFields().end(); it++) {
        (*it)->accept(m_this);
    }
    m_depth--;

    generate_suffix(i);
}

void TaskGenerateExecModelStructInit::generate_suffix(vsc::dm::IDataTypeStruct *i) {
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");
}

void TaskGenerateExecModelStructInit::visitDataTypeAddrClaim(arl::dm::IDataTypeAddrClaim *t) {
    DEBUG_ENTER("visitDataTypeAddrClaim");
    if (m_depth) {
        m_out_c->println("this_p->%s.claim = zsp_rt_addr_claim_new(&actor->actor);", 
            m_gen->getNameMap()->getName(m_field).c_str());
    }
    DEBUG_LEAVE("visitDataTypeAddrClaim");
}

void TaskGenerateExecModelStructInit::visitDataTypeArray(vsc::dm::IDataTypeArray *t) {}

void TaskGenerateExecModelStructInit::visitDataTypeBool(vsc::dm::IDataTypeBool *t) {

}

void TaskGenerateExecModelStructInit::visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) {}

void TaskGenerateExecModelStructInit::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    if (m_depth) {
        m_out_c->println("this_p->%s = 0;", m_gen->getNameMap()->getName(m_field).c_str());
    }
}

void TaskGenerateExecModelStructInit::visitDataTypePtr(vsc::dm::IDataTypePtr *t) {}

void TaskGenerateExecModelStructInit::visitDataTypeString(vsc::dm::IDataTypeString *t) {}

void TaskGenerateExecModelStructInit::visitTypeField(vsc::dm::ITypeField *f) {
    DEBUG_ENTER("visitTypeField %s", f->name().c_str());
    m_field = f;
    f->getDataType()->accept(m_this);
    DEBUG_LEAVE("visitTypeField %s", f->name().c_str());
}

void TaskGenerateExecModelStructInit::visitTypeFieldRegGroup(arl::dm::ITypeFieldRegGroup *f) {
    DEBUG_ENTER("visitTypeFieldRegGroup");
    DEBUG("TODO: visitTypeFieldRegGroup");
    DEBUG_LEAVE("visitTypeFieldRegGroup");
}


}
}
}
