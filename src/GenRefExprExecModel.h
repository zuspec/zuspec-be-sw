/**
 * GenRefExprExecModel.h
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
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "IGenRefExpr.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;


class GenRefExprExecModel : 
    public virtual IGenRefExpr,
    public virtual arl::dm::VisitorBase {
public:
    GenRefExprExecModel(
        TaskGenerateExecModel       *gen,
        vsc::dm::IDataTypeStruct    *ctxt,
        const std::string           &ctxtRef,
        bool                        ctxtPtr,
        const std::string           &bupRef="",
        bool                        bupPtr=false
    );

    virtual ~GenRefExprExecModel();

    virtual std::string genLval(vsc::dm::ITypeExpr *ref) override;

    virtual std::string genRval(vsc::dm::ITypeExpr *ref) override;

    virtual bool isFieldRefExpr(vsc::dm::ITypeExpr *ref) override;

    virtual bool isRefFieldRefExpr(vsc::dm::ITypeExpr *ref) override;
    
    virtual void pushScope(arl::dm::ITypeProcStmtScope *s) override {
        m_scope_s.push_back(s);
    }

    virtual void popScope() override {
        m_scope_s.pop_back();
    }

	virtual void visitTypeExprRefBottomUp(vsc::dm::ITypeExprRefBottomUp *e) override;

	virtual void visitTypeExprRefPath(vsc::dm::ITypeExprRefPath *e) override;

	virtual void visitTypeExprRefTopDown(vsc::dm::ITypeExprRefTopDown *e) override;

	virtual void visitTypeExprSubField(vsc::dm::ITypeExprSubField *e) override;

	virtual void visitTypeField(vsc::dm::ITypeField *f) override;

	virtual void visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) override;

	virtual void visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) override;


private:
    static dmgr::IDebug                             *m_dbg;
    TaskGenerateExecModel                           *m_gen;
    vsc::dm::IDataTypeStruct                        *m_ctxt;
    std::string                                     m_ctxtRef;
    bool                                            m_ctxtPtr;
    std::string                                     m_bupRef;
    bool                                            m_bupPtr;
    std::string                                     m_ret;
    vsc::dm::IDataType                              *m_type;
    int32_t                                         m_depth;
    bool                                            m_isRef;
    bool                                            m_isFieldRef;
    bool                                            m_isRefFieldRef;
    std::vector<arl::dm::ITypeProcStmtScope *>      m_scope_s;

};

}
}
}


