/*
 * TaskGenerateCompInit.cpp
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
#include "TaskGenerateCompInit.h"
#include "TaskGenerateExecBlockNB.h"
#include "GenRefExprExecModel.h"


namespace zsp {
namespace be {
namespace sw {

TaskGenerateCompInit::TaskGenerateCompInit(
    IContext *ctxt, 
    TypeInfo *info, 
    IOutput *out_h, 
    IOutput *out_c) : TaskGenerateStructInit(ctxt, /*info,*/ out_h, out_c) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateCompInit", ctxt->getDebugMgr());
    m_mode = Mode::DataFieldInit;
}

TaskGenerateCompInit::~TaskGenerateCompInit() {

}

void TaskGenerateCompInit::generate_prefix(vsc::dm::IDataTypeStruct *i) {
    m_out_h->println("void %s__init(struct zsp_init_ctxt_s *ctxt, struct %s_s *this_p, const char *name, zsp_component_t *parent);",
        m_ctxt->nameMap()->getName(i).c_str(),
        m_ctxt->nameMap()->getName(i).c_str());

    m_out_c->println("void %s__init(struct zsp_init_ctxt_s *ctxt, struct %s_s *this_p, const char *name, zsp_component_t *parent) {",
        m_ctxt->nameMap()->getName(i).c_str(),
        m_ctxt->nameMap()->getName(i).c_str());
    m_out_c->inc_ind();
}

void TaskGenerateCompInit::generate_core(vsc::dm::IDataTypeStruct *i) {
    DEBUG_ENTER("generate_core");
    if (i->getSuper()) {
        m_out_c->println("%s__init(ctxt, &this_p->super, name, parent);",
            m_ctxt->nameMap()->getName(i->getSuper()).c_str());
    } else {
        generate_default_init(i);
    }
    // Initialize the type pointer 
    m_out_c->println("((zsp_object_t *)this_p)->type = (zsp_object_type_t *)%s__type();",
        m_ctxt->nameMap()->getName(i).c_str());
    DEBUG_LEAVE("generate_core"); 
}

void TaskGenerateCompInit::generate_default_init(vsc::dm::IDataTypeStruct *i) {
    m_out_c->println("zsp_component_init(ctxt, &this_p->super, name, parent);");
}

void TaskGenerateCompInit::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent");
    if (!m_is_ref) {
        m_out_c->println("%s__init(ctxt, &this_p->%s, \"%s\", (zsp_component_t *)this_p);",
            m_ctxt->nameMap()->getName(t).c_str(),
            m_field->name().c_str(),
            m_field->name().c_str());
    } else {
        // TODO:
    }

    DEBUG_LEAVE("visitDataTypeComponent");
}

}
}
}
