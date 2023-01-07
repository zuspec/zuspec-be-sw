/*
 * TaskGenerateEmbCVarDecl.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include "vsc/dm/impl/TaskIsTypeFieldRef.h"
#include "TaskGenerateEmbCVarDecl.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateEmbCVarDecl::TaskGenerateEmbCVarDecl(
    IOutput             *out,
    NameMap             *name_m) : m_out(out), m_name_m(name_m),
        m_dt_gen(out, name_m) {

}

TaskGenerateEmbCVarDecl::~TaskGenerateEmbCVarDecl() {

}

void TaskGenerateEmbCVarDecl::generate(arl::dm::ITypeProcStmt *stmt) {
    stmt->accept(m_this);
}

void TaskGenerateEmbCVarDecl::generate(
        vsc::dm::IDataType          *type,
        vsc::dm::ITypeField         *field) {
    m_out->indent();
    m_dt_gen.generate(type);
    m_out->write(" %s%s;\n", 
        vsc::dm::TaskIsTypeFieldRef().eval(field)?"*":"",
        field->name().c_str());
}
 
void TaskGenerateEmbCVarDecl::visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) {
    // Don't recurse
}

void TaskGenerateEmbCVarDecl::visitTypeProcStmtVarDecl(arl::dm::ITypeProcStmtVarDecl *s) {
    m_out->indent();
    m_dt_gen.generate(s->getDataType());
    m_out->write(" %s", s->name().c_str());

    if (s->getInit()) {
        // TODO: write initial value
    }
    m_out->write(";\n");
}

}
}
}

