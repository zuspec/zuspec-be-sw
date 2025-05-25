/*
 * TaskGenerateExecModelCompExecInit.cpp
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
#include "TaskDefinesAddrSpace.h"
#include "GenRefExprExecModel.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelCompExecInit.h"
#include "TaskGenerateExecBlockNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelCompExecInit::TaskGenerateExecModelCompExecInit(
        TaskGenerateExecModel       *gen,
        IOutput                     *out) : m_gen(gen), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelCompExecInit", gen->getDebugMgr());
}

TaskGenerateExecModelCompExecInit::~TaskGenerateExecModelCompExecInit() {

}

void TaskGenerateExecModelCompExecInit::generate (arl::dm::IDataTypeComponent *t) {
    GenRefExprExecModel refgen(
        m_gen->getDebugMgr(), 
        t,
        "this_p",
        true);

    const std::vector<arl::dm::ITypeExecUP> &init_down = 
        t->getExecs(arl::dm::ExecKindT::InitDown);
    const std::vector<arl::dm::ITypeExecUP> &init_up = 
        t->getExecs(arl::dm::ExecKindT::InitUp);

    // // First, generate exec init_* functions if we'll be calling them
    // if (init_down.size()) {
    //     // Invoke the init_down exec block
    //     TaskGenerateExecModelExecBlockNB(m_gen, &refgen, m_out).generate(
    //         m_gen->getNameMap()->getName(t) + "__init_down",
    //         "struct " + m_gen->getNameMap()->getName(t) + "_s",
    //         init_down
    //     );
    // }
    // if (init_up.size()) {
    //     // Invoke the init_up exec block
    //     TaskGenerateExecModelExecBlockNB(m_gen, &refgen, m_out).generate(
    //         m_gen->getNameMap()->getName(t) + "__init_up",
    //         "struct " + m_gen->getNameMap()->getName(t) + "_s",
    //         init_down
    //     );
    // }

    m_out->println("void %s__exec_init(%s_t *actor, %s_init_t *init_data, zsp_rt_aspace_idx_t *__aspace, %s_t *this_p) {",
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());
    m_out->inc_ind();

    // First off, add ourselves to the component-inst list and record
    // our base offset
    m_out->println("this_p->comp.comp_id = init_data->comp_idx;");
    m_out->println("actor->comp_insts[init_data->comp_idx++] = &this_p->comp;");

    for (uint32_t i=0; i<m_gen->getNumTraitTypes(); i++) {
        m_out->println("this_p->__aspace[%d] = __aspace[%d];", i, i);
    }

    // Now, evaluate init_down exec blocks
    if (init_down.size()) {
        m_out->println("%s__init_down(actor, this_p);", 
            m_gen->getNameMap()->getName(t).c_str());
    }

    // Call exec-init for all component-type fields 
    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=t->getFields().begin();
        it!=t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }

    // Finally, evaluate init_up exec blocks
    if (init_up.size()) {
        m_out->println("%s__init_up(actor, this_p);", 
            m_gen->getNameMap()->getName(t).c_str());
    }

    m_out->dec_ind();
    m_out->println("}");

}

void TaskGenerateExecModelCompExecInit::visitDataTypeAddrSpaceC(arl::dm::IDataTypeAddrSpaceC *t) {
    m_out->println("this_p->__aspace[%d] = init_data->aspace_idx;",
        m_gen->getTraitTypeId(t->getTraitType()));
    m_out->println("actor->aspace_insts[init_data->aspace_idx++] = (zsp_rt_addr_space_t *)&this_p->%s;",
        m_field->name().c_str());
}

void TaskGenerateExecModelCompExecInit::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent");
    m_out->println("%s__exec_init(actor, init_data, this_p->__aspace, &this_p->%s);",
        m_gen->getNameMap()->getName(t).c_str(),
        m_field->name().c_str());
    DEBUG_LEAVE("visitDataTypeComponent");
}

void TaskGenerateExecModelCompExecInit::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *t) {
    DEBUG_ENTER("visitTypeFieldPhy %s", t->name().c_str());
    m_field = t;
    t->getDataType()->accept(m_this);
    m_field = 0;
    DEBUG_LEAVE("visitTypeFieldPhy %s", t->name().c_str());
}

dmgr::IDebug *TaskGenerateExecModelCompExecInit::m_dbg = 0;

}
}
}
