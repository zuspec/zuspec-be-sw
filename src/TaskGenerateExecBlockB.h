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

    virtual void visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *s) override;

    virtual void visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) override;

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;

private:
    static dmgr::IDebug                 *m_dbg;
    IContext                            *m_ctxt;
    IGenRefExpr                         *m_refgen;
    IOutput                             *m_out_h;
    IOutput                             *m_out_c;
    bool                                m_expr_terminated;
    TypeProcStmtAsyncScope              *m_scope;
    std::string                         m_fname;

};

}
}
}


