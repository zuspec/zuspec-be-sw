/*
 * TypeProcStmtAsyncScope.cpp
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
#include "zsp/arl/dm/IVisitor.h"
#include "IVisitor.h"
#include "TypeProcStmtAsyncScope.h"


namespace zsp {
namespace be {
namespace sw {


TypeProcStmtAsyncScope::TypeProcStmtAsyncScope(int32_t id) : m_id(id) {

}

TypeProcStmtAsyncScope::~TypeProcStmtAsyncScope() {

}

void TypeProcStmtAsyncScope::addStatement(IAccept *stmt, bool owned) {
    m_statements.push_back(vsc::dm::IAcceptUP(stmt, owned));
}

#ifdef UNDEFINED
void TypeProcStmtAsyncScope::insertStatement(
        int32_t                 i,
        ITypeProcStmt           *stmt) {
    m_statements.insert(
        m_statements.begin()+i,
        arl::dm::ITypeProcStmtUP(stmt));
}

int32_t TypeProcStmtAsyncScope::addVariable(vsc::dm::ITypeVar *v, bool owned) {
    /*
    m_statements.push_back(ITypeProcStmtUP(dynamic_cast<ITypeProcStmt *>(v)));
    int32_t ret = m_variables.size();
    m_variables.push_back(vsc::dm::ITypeVarUP(v, false));
    if (!m_locals_t) {
        m_locals_t = vsc::dm::IDataTypeStructUP(m_ctxt->mkDataTypeStruct(""));
    }
    m_locals_t->addField(m_ctxt->mkTypeFieldPhy(
        v->name(),
        v->getDataType(),
        false,
        vsc::dm::TypeFieldAttr::NoAttr, 
        0 // ->getInit()
    ));

    return ret;
     */
    return -1;
}

#endif // UNDEFINED

void TypeProcStmtAsyncScope::accept(vsc::dm::IVisitor *v) {
    if (dynamic_cast<IVisitor *>(v)) {
        dynamic_cast<IVisitor *>(v)->visitTypeProcStmtAsyncScope(this);
    }// else if (dynamic_cast<arl::dm::IVisitor *>(v)) {
//        dynamic_cast<arl::dm::IVisitor *>(v)->visitTypeProcStmtScope(this);
//    }
}

}
}
}
