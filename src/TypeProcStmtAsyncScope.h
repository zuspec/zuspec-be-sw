/**
 * TypeProcStmtAsyncScope.h
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
#include "vsc/dm/ITypeVar.h"
#include "zsp/arl/dm/ITypeProcStmtScope.h"

namespace zsp {
namespace be {
namespace sw {

class TypeProcStmtAsyncScope;
using TypeProcStmtAsyncScopeUP=vsc::dm::UP<TypeProcStmtAsyncScope>;
class TypeProcStmtAsyncScope :
    public virtual arl::dm::ITypeProcStmtScope {
public:
    TypeProcStmtAsyncScope(int32_t id);

    TypeProcStmtAsyncScope(
        int32_t                                     id,
        const std::vector<vsc::dm::ITypeVarScope *> &scope);

    virtual ~TypeProcStmtAsyncScope();

    int32_t id() const { return m_id; }

    void pushScope(vsc::dm::ITypeVarScope *scope);

    const std::vector<vsc::dm::ITypeVarScope *> &scopes() const { return m_scopes; }

    virtual void addStatement(ITypeProcStmt *stmt, bool owned=true) override;

    virtual int32_t addVariable(vsc::dm::ITypeVar *v, bool owned=true) override;

    virtual int32_t getNumVariables() override { return -1; }

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

    virtual void setAssociatedData(vsc::dm::IAssociatedData *data) override {
        m_assoc_data = vsc::dm::IAssociatedDataUP(data);
    }

    virtual vsc::dm::IAssociatedData *getAssociatedData() const override {
        return m_assoc_data.get();
    }

    virtual void accept(vsc::dm::IVisitor *v) override;

private:
    int32_t                                 m_id;
    std::vector<arl::dm::ITypeProcStmtUP>   m_statements;
    std::vector<vsc::dm::ITypeVarScope *>   m_scopes;
    vsc::dm::IAssociatedDataUP              m_assoc_data;

};

}
}
}


