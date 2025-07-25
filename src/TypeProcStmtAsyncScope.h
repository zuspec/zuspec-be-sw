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
#include "vsc/dm/impl/ValRef.h"
#include "zsp/arl/dm/ITypeProcStmtScope.h"
#include "zsp/arl/dm/IDataTypeActivity.h"

namespace zsp {
namespace be {
namespace sw {

class TypeProcStmtAsyncScope;
using TypeProcStmtAsyncScopeUP=vsc::dm::UP<TypeProcStmtAsyncScope>;
class TypeProcStmtAsyncScope : 
    public virtual vsc::dm::IAccept,
    public virtual arl::dm::ITypeProcStmt,
    public virtual arl::dm::IDataTypeActivity {
public:
    TypeProcStmtAsyncScope(int32_t id);

    virtual ~TypeProcStmtAsyncScope();

    int32_t id() const { return m_id; }

    void setId(int32_t i) { m_id = i; }

	virtual arl::dm::IModelActivity *mkActivity(
		vsc::dm::IModelBuildContext		*ctxt,
		arl::dm::ITypeFieldActivity			*type) override { return 0; }

    virtual void addStatement(IAccept *stmt, bool owned=true);

#ifdef UNDEFINED
//    virtual int32_t addVariable(vsc::dm::ITypeVar *v, bool owned=true) override;

    virtual int32_t getNumVariables() override { return -1; }

    virtual const std::vector<vsc::dm::ITypeVarUP> &getVariables() const override { }

    virtual void insertStatement(
        int32_t                 i,
        arl::dm::ITypeProcStmt  *s) override;

    virtual int32_t insertVariable(
        int32_t                         i,
        arl::dm::ITypeProcStmtVarDecl   *s) override { };
#endif /* UNDEFINED */

    virtual const std::vector<vsc::dm::IAcceptUP> &getStatements() const {
        return m_statements;
    }

	virtual void finalize(vsc::dm::IContext *ctxt) override { }

    virtual int32_t getByteSize() const override { return -1; }

	virtual vsc::dm::IModelField *mkRootField(
		vsc::dm::IModelBuildContext	*ctxt,
		const std::string	&name,
		bool				is_ref) override { return 0; }

	virtual vsc::dm::IModelField *mkTypeField(
		vsc::dm::IModelBuildContext	*ctxt,
		vsc::dm::ITypeField			*type,
        const vsc::dm::ValRef        &val) override { return 0; }

    virtual void initVal(vsc::dm::ValRef &v) override { }

    virtual void finiVal(vsc::dm::ValRef &v) override { }

    virtual vsc::dm::ValRef copyVal(const vsc::dm::ValRef &src) override { return vsc::dm::ValRef(); }

    virtual vsc::dm::IValIterator *mkValIterator(const vsc::dm::ValRef &src) override { return 0; }

    virtual vsc::dm::IValMutIterator *mkValMutIterator(const vsc::dm::ValRef &src) override { return 0; }

//    virtual vsc::dm::IDataTypeStruct *getLocalsT() const override { return 0; }

    virtual void setAssociatedData(vsc::dm::IAssociatedData *data, bool owned=true) {
        m_assoc_data = vsc::dm::IAssociatedDataUP(data, owned);
    }

    virtual vsc::dm::IAssociatedData *getAssociatedData() const {
        return m_assoc_data.get();
    }

    virtual void accept(vsc::dm::IVisitor *v) override;

private:
    int32_t                                 m_id;
    std::vector<vsc::dm::IAcceptUP>         m_statements;
    vsc::dm::IAssociatedDataUP              m_assoc_data;

};

}
}
}


