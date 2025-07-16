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
#include "TaskGenerateAsyncBase.h"

namespace zsp {
namespace be {
namespace sw {

class ScopeLocalsAssociatedData;
class TaskGenerateExecModel;

class TaskGenerateExecBlockB :
    public virtual TaskGenerateAsyncBase {
public:
    TaskGenerateExecBlockB(
        IContext                    *ctxt,
        IGenRefExpr                 *refgen,
        IOutput                     *out_h,
        IOutput                     *out_c,
        const std::string           &fname);

    virtual ~TaskGenerateExecBlockB();

    void generate(const std::vector<arl::dm::ITypeExecUP> &execs);

    virtual void visitTypeProcStmtAssign(arl::dm::ITypeProcStmtAssign *s) override;

    virtual void visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *s) override;

    virtual void visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) override;

    virtual void visitTypeProcStmtGotoAsyncScope(TypeProcStmtGotoAsyncScope *s) override;

    virtual void visitTypeProcStmtIfElse(arl::dm::ITypeProcStmtIfElse *s) override;

    virtual void visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) override;

    virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) override;

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;


private:
    IOutput                             *m_out_h;

};

}
}
}


