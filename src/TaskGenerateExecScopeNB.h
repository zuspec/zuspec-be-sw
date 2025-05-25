/**
 * TaskGenerateExecScopeNB.h
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
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/ITypeExec.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "IGenRefExpr.h"
#include "OutputExecScope.h"


namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExecScopeNB : public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecScopeNB(
        IContext                *gen,
        IGenRefExpr             *refgen,
        IOutput                 *out);

    virtual ~TaskGenerateExecScopeNB();

    virtual void generate(
        arl::dm::ITypeExec                      *i,
        bool                                    new_scope);

    virtual void generate(
        arl::dm::ITypeProcStmt                  *i,
        bool                                    new_scope);

    virtual void generate(
        const std::vector<arl::dm::ITypeExecUP> &i,
        bool                                    new_scope);

	virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) override;

	virtual void visitTypeProcStmtAssign(arl::dm::ITypeProcStmtAssign *s) override;

	virtual void visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) override;

	virtual void visitTypeProcStmtIfClause(arl::dm::ITypeProcStmtIfClause *s) override;

	virtual void visitTypeProcStmtIfElse(arl::dm::ITypeProcStmtIfElse *s) override;

	virtual void visitTypeProcStmtVarDecl(arl::dm::ITypeProcStmtVarDecl *s) override;

    virtual void visitDataTypeAddrClaim(arl::dm::IDataTypeAddrClaim *t) override;

    virtual void visitDataTypeAddrHandle(arl::dm::IDataTypeAddrHandle *t) override;

protected:
    dmgr::IDebug                        *m_dbg;
    IContext                            *m_ctxt;
    IGenRefExpr                         *m_refgen;
    IOutput                             *m_out;
    std::vector<OutputExecScope>        m_out_s;
    arl::dm::ITypeProcStmtVarDecl       *m_var;
    vsc::dm::ITypeExpr                  *m_expr;

};

}
}
}


