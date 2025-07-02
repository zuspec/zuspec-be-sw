/*
 * TaskGenerateCompDoInit.cpp
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
#include "TaskGenerateCompDoInit.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateCompDoInit::TaskGenerateCompDoInit(
        IContext                *ctxt,
        TypeInfo                *info,
        IOutput                 *out_h,
        IOutput                 *out_c) : 
        m_ctxt(ctxt), m_info(info), m_out_h(out_h), m_out_c(out_c) {

}

TaskGenerateCompDoInit::~TaskGenerateCompDoInit() {

}

void TaskGenerateCompDoInit::generate(vsc::dm::IDataTypeStruct *t) {
    m_out_h->println("void %s__do_init(struct zsp_executor_s *exec_b, %s_t *self);", 
        m_ctxt->nameMap()->getName(t).c_str(),
        m_ctxt->nameMap()->getName(t).c_str());

    m_out_c->println("void %s__do_init(struct zsp_executor_s *exec_b, %s_t *self) {", 
        m_ctxt->nameMap()->getName(t).c_str(),
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->inc_ind();

    m_out_c->println("zsp_component(self)->default_executor = exec_b;");

    m_out_c->println("%s__init_down(exec_b, self);",
        m_ctxt->nameMap()->getName(t).c_str());

    for (auto it=t->getFields().begin();
            it!=t->getFields().end(); it++) {
        (*it)->accept(this);
    }

    m_out_c->println("%s__init_up(exec_b, self);",
        m_ctxt->nameMap()->getName(t).c_str());

    m_out_c->dec_ind();
    m_out_c->println("}");

}

void TaskGenerateCompDoInit::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    if (m_is_ref) {
        // TODO:
    } else {
        m_out_c->println("zsp_component_type(&self->%s)->do_init(exec_b, (zsp_struct_t *)&self->%s);",
            m_ctxt->nameMap()->getName(m_field).c_str(),
            m_ctxt->nameMap()->getName(m_field).c_str());
    }

}

void TaskGenerateCompDoInit::visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) {
    m_field = f;
    m_is_ref = false;
    f->getDataType()->accept(this);
}

void TaskGenerateCompDoInit::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    m_field = f;
    m_is_ref = true;
    f->getDataType()->accept(this);
}

}
}
}
