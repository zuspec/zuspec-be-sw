/**
 * TaskBuildAsyncScopeGroup.h
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
#include <set>
#include <vector>
#include "vsc/dm/ITypeFieldPhy.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IContext.h"
#include "TypeProcStmtAsyncScope.h"
#include "TypeProcStmtAsyncScopeGroup.h"

namespace zsp {
namespace be {
namespace sw {

class TaskBuildAsyncScopeGroup :
    public virtual arl::dm::VisitorBase {
public:
    TaskBuildAsyncScopeGroup(IContext *ctxt);

    virtual ~TaskBuildAsyncScopeGroup();

    virtual TypeProcStmtAsyncScopeGroup *build(vsc::dm::IAccept *scope);

    virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) override;

    virtual void visitDataTypeActivity(arl::dm::IDataTypeActivity *t) override;

    virtual void visitDataTypeActivitySequence(arl::dm::IDataTypeActivitySequence *t) override;

    virtual void visitDataTypeActivityTraverseType(arl::dm::IDataTypeActivityTraverseType *t) override;

    virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

	virtual void visitTypeExprBin(vsc::dm::ITypeExprBin *e) override;

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;

    virtual void visitTypeExecProc(arl::dm::ITypeExecProc *e) override;

    virtual void visitTypeProcStmt(arl::dm::ITypeProcStmt *s) override;

    virtual void visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) override;

	virtual void visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) override;

	virtual void visitTypeProcStmtRepeatWhile(arl::dm::ITypeProcStmtRepeatWhile *s) override;

    virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) override;

	virtual void visitTypeProcStmtWhile(arl::dm::ITypeProcStmtWhile *s) override;

	virtual void visitTypeProcStmtYield(arl::dm::ITypeProcStmtYield *s) override;

private:
    struct Locals {

        Locals(
            vsc::dm::ITypeVarScope      *scope, 
            Locals                      *upper,
            vsc::dm::IDataTypeStruct    *type=0) {
            this->scope = scope;
            this->type = type;
            this->upper = upper;
            this->tmpid = 0;
        }

        vsc::dm::ITypeVarScope         *scope;
        vsc::dm::IDataTypeStruct       *type;
        Locals                         *upper;
        std::vector<Locals *>          children;
        int32_t                        tmpid;
    };

private:
    using AssocDataAccL=std::vector<vsc::dm::IAssociatedDataAcc *>;
    using ScopeSpec=std::vector<vsc::dm::ITypeVarScope *>;

private:

    TypeProcStmtAsyncScope *currentScope() {
        return m_scopes.at(m_scopes.size()-2).get();
    }

    TypeProcStmtAsyncScope *newScope();

    void enter_scope(vsc::dm::ITypeVarScope *scope);

    void visit_stmt(arl::dm::ITypeProcStmt *s);

    void leave_scope();

    vsc::dm::IDataTypeStruct *mk_type();

    void build_scope_types(Locals *l);

    vsc::dm::ITypeVar *mk_temp(vsc::dm::IDataType *type, bool owned);

    void add_fields(
        vsc::dm::IDataTypeStruct    *type, 
        Locals                      *l,
        std::set<std::string>       &names,
        int32_t                     &shadow_id);

private:
    static dmgr::IDebug                         *m_dbg;
    IContext                                    *m_ctxt;
    vsc::dm::ITypeExprUP                        m_expr;
    std::vector<TypeProcStmtAsyncScopeUP>       m_scopes;
    std::vector<vsc::dm::ITypeVarScope *>       m_scope_s;
    Locals                                      *m_locals_root;
    std::vector<Locals *>                       m_locals_s;
    std::vector<vsc::dm::IDataTypeStructUP>     m_locals_type_l;
    std::vector<ScopeSpec>                      m_locals_scope_l;
    std::vector<arl::dm::ITypeProcStmtScopeUP>  m_vscopes;

};

}
}
}


