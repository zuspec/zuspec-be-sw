/*
 * TaskGenerateExecModelUpdateRCField.cpp
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
#include "TaskGenerateExecModelUpdateRCField.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelUpdateRCField::TaskGenerateExecModelUpdateRCField(
    IGenRefExpr         *refgen) : m_refgen(refgen) {

}

TaskGenerateExecModelUpdateRCField::~TaskGenerateExecModelUpdateRCField() {

}

void TaskGenerateExecModelUpdateRCField::generate_acquire(
        IOutput             *out,
        vsc::dm::IDataType  *type,
        vsc::dm::ITypeExpr  *expr) {
    m_out_s = 0;
    m_out = out;
    m_expr = expr;
    m_var = 0;
    m_kind = Kind::Acquire;

    type->accept(m_this);
}

void TaskGenerateExecModelUpdateRCField::generate_acquire(
        IOutput                         *out,
        arl::dm::ITypeProcStmtVarDecl   *var) {
    m_out_s = 0;
    m_out = out;
    m_expr = 0;
    m_var = var;
    m_kind = Kind::Acquire;

    var->getDataType()->accept(m_this);
}
        
void TaskGenerateExecModelUpdateRCField::generate_release(
        IOutput             *out,
        vsc::dm::IDataType  *type,
        vsc::dm::ITypeExpr  *expr) {
    m_out_s = 0;
    m_out = out;
    m_expr = expr;
    m_var = 0;
    m_kind = Kind::Release;

    type->accept(m_this);
}

void TaskGenerateExecModelUpdateRCField::generate_release(
        IOutput                         *out,
        arl::dm::ITypeProcStmtVarDecl   *var) {
    m_out_s = 0;
    m_out = out;
    m_expr = 0;
    m_var = var;
    m_kind = Kind::Release;

    var->getDataType()->accept(m_this);
}
        
void TaskGenerateExecModelUpdateRCField::generate_acquire_dtor(
        OutputExecScope                 *out,
        arl::dm::ITypeProcStmtVarDecl   *var) {
    m_out_s = out;
    m_out = 0;
    m_expr = 0;
    m_var = var;
    m_kind = Kind::AcquireDtor;

    var->getDataType()->accept(m_this);
}

void TaskGenerateExecModelUpdateRCField::generate_dtor(
        OutputExecScope                 *out,
        arl::dm::ITypeProcStmtVarDecl   *var) {
    m_out_s = out;
    m_out = 0;
    m_expr = 0;
    m_var = var;
    m_kind = Kind::Dtor;

    var->getDataType()->accept(m_this);
}

void TaskGenerateExecModelUpdateRCField::visitDataTypeAddrHandle(arl::dm::IDataTypeAddrHandle *t) {
    switch (m_kind) {
        case Kind::Acquire: {
            if (m_expr) {
                m_out->println("zsp_rt_rc_inc(%s.store);",
                    m_refgen->genRval(m_expr).c_str());
            } else {
                m_out->println("zsp_rt_rc_inc(%s.store);", m_var->name().c_str());
            }
        } break;
        case Kind::Release: {
            if (m_expr) {
                m_out->println("zsp_rt_rc_dec(%s.store);",
                    m_refgen->genRval(m_expr).c_str());
            } else {
                m_out->println("zsp_rt_rc_dec(%s.store);", m_var->name().c_str());
            }
        } break;
        case Kind::AcquireDtor: {
            m_out_s->exec()->println("zsp_rt_rc_inc(%s.store);",
                m_var->name().c_str());
            m_out_s->dtor()->println("zsp_rt_rc_dec(%s.store);",
                m_var->name().c_str());
        } break;
        case Kind::Dtor: {
            if (m_expr) {
                m_out_s->dtor()->println("zsp_rt_rc_dec(%s.store);",
                    m_refgen->genRval(m_expr).c_str());
            } else {
                m_out_s->dtor()->println("zsp_rt_rc_dec(%s.store);",
                    m_var->name().c_str());
            }
        } break;
    }
}

}
}
}
