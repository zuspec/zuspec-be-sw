/*
 * TaskGenerateActionType.cpp
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
#include "TaskGenerateActionType.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateActionType::TaskGenerateActionType(
        IContext                    *ctxt, 
        IOutput                     *out_h,
        IOutput                     *out_c) : TaskGenerateStructType(ctxt, out_h, out_c) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateActionType", ctxt->getDebugMgr());
}

TaskGenerateActionType::~TaskGenerateActionType() {

}

void TaskGenerateActionType::generate(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("generate");
    generate_type_decl(t);
    generate_type_inst(t);
    DEBUG_LEAVE("generate");
}

void TaskGenerateActionType::generate_type_decl(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("generate_type_decl");
    m_out_h->println("typedef struct %s__type_s {", 
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_h->inc_ind();

    if (t->getSuper()) {
        m_out_h->println("%s__type_t base;", 
            m_ctxt->nameMap()->getName(t->getSuper()).c_str());
    } else {
        m_out_h->println("zsp_action_type_t base;");
    }

    // Must add method declarations (if applicable)
    m_out_h->dec_ind();
    m_out_h->println("} %s__type_t;",
        m_ctxt->nameMap()->getName(t).c_str());

    m_out_h->println("");

    m_out_h->println("%s__type_t *%s__type();",
        m_ctxt->nameMap()->getName(t).c_str(),
        m_ctxt->nameMap()->getName(t).c_str());

    DEBUG_LEAVE("generate_type_decl");
}

void TaskGenerateActionType::generate_type_inst(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("generate_type_inst");

    m_out_c->println("%s__type_t *%s__type() {",
        m_ctxt->nameMap()->getName(t).c_str(),
        m_ctxt->nameMap()->getName(t).c_str());

    m_out_c->inc_ind();
    m_out_c->println("static int __init = 0;");
    m_out_c->println("static %s__type_t __type;",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("if (__init == 0) {");
    m_out_c->inc_ind();
    if (t->getSuper()) {
        m_out_c->println("((zsp_object_type_t *)&__type)->super = %s__type();",
            m_ctxt->nameMap()->getName(t->getSuper()).c_str());
    } else {
        m_out_c->println("((zsp_object_type_t *)&__type)->super = 0;");
    }

    m_out_c->println("((zsp_object_type_t *)&__type)->name = \"%s\";",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("((zsp_object_type_t *)&__type)->dtor = (zsp_dtor_f)&%s__dtor;",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("((zsp_struct_type_t *)&__type)->pre_solve = (zsp_solve_exec_f)&%s__pre_solve;",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("((zsp_struct_type_t *)&__type)->post_solve = (zsp_solve_exec_f)&%s__post_solve;",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("((zsp_struct_type_t *)&__type)->pre_body = (zsp_solve_exec_f)&%s__pre_body;",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("((zsp_action_type_t *)&__type)->body = (zsp_task_func)&%s__body;",
        m_ctxt->nameMap()->getName(t).c_str());
    m_out_c->println("__init = 1;");
    m_out_c->dec_ind();
    m_out_c->println("}");

    m_out_c->println("return &__type;");
    m_out_c->dec_ind();
    m_out_c->println("}");

    DEBUG_LEAVE("generate_type_inst");
}

}
}
}
