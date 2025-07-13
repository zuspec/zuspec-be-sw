/**
 * TaskGenerateExecBlockB.h
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
#include <string>
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/ITypeExec.h"
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "IGenRefExpr.h"
#include "VisitorBase.h"

namespace zsp {
namespace be {
namespace sw {

class ScopeLocalsAssociatedData;
class TaskGenerateExecModel;

class TaskGenerateExecBlockB :
    public virtual VisitorBase {
public:
    TaskGenerateExecBlockB(
        IContext                    *ctxt,
        IGenRefExpr                 *refgen,
        IOutput                     *out_h,
        IOutput                     *out_c);

    virtual ~TaskGenerateExecBlockB();

    void generate(
        const std::string                           &fname,
        const std::string                           &tname,
        const std::vector<arl::dm::ITypeExecUP>     &execs);

    virtual void visitTypeProcStmtAssign(arl::dm::ITypeProcStmtAssign *s) override;

    virtual void visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *s) override;

    virtual void visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) override;

    virtual void visitTypeProcStmtGotoAsyncScope(TypeProcStmtGotoAsyncScope *s) override;

    virtual void visitTypeProcStmtIfElse(arl::dm::ITypeProcStmtIfElse *s) override;

    virtual void visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) override;

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;

protected:
    virtual void enter_stmt(arl::dm::ITypeProcStmt *s);

private:
    static dmgr::IDebug                 *m_dbg;
    IContext                            *m_ctxt;
    IGenRefExpr                         *m_refgen;
    IOutput                             *m_out_h;
    IOutput                             *m_out_c;
    bool                                m_expr_terminated;
    ScopeLocalsAssociatedData           *m_scope;
    vsc::dm::IDataTypeStruct            *m_largest_locals;
    std::vector<vsc::dm::ITypeVarScope *>   m_scope_s;
    int32_t                             m_next_scope_id;
    vsc::dm::IDataTypeStruct            *m_locals_t;
    std::string                         m_fname;

};

}
}
}


