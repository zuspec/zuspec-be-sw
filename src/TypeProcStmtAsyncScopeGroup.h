/**
 * TypeProcStmtAsyncScopeGroup.h
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
#pragma once
#include "zsp/arl/dm/ITypeProcStmtScope.h"

namespace zsp {
namespace be {
namespace sw {

class TypeProcStmtAsyncScopeGroup;
using TypeProcStmtAsyncScopeGroupUP=vsc::dm::UP<TypeProcStmtAsyncScopeGroup>;
class TypeProcStmtAsyncScopeGroup :
    public virtual arl::dm::ITypeProcStmtScope {
public:
    TypeProcStmtAsyncScopeGroup();

    virtual ~TypeProcStmtAsyncScopeGroup();

    virtual void addStatement(ITypeProcStmt *stmt, bool owned=true) override;

    virtual int32_t addVariable(vsc::dm::ITypeVar *v, bool owned=true) override;

    virtual int32_t getNumVariables() override { return 0; }

    virtual const std::vector<vsc::dm::ITypeVarUP> &getVariables() const override { }

    virtual void insertStatement(
        int32_t                 i,
        arl::dm::ITypeProcStmt  *s) override;

    virtual int32_t insertVariable(
        int32_t                         i,
        arl::dm::ITypeProcStmtVarDecl   *s) override { };

    virtual const std::vector<arl::dm::ITypeProcStmtUP> &getStatements() const override {
        return m_statements;
    }

    virtual vsc::dm::IDataTypeStruct *getLocalsT() const override { return 0; }

    virtual void accept(vsc::dm::IVisitor *v) override;

private:
    std::vector<arl::dm::ITypeProcStmtUP>   m_statements;

};

}
}
}


