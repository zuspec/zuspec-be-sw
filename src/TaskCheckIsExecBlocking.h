/**
 * TaskCheckIsExecBlocking.h
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

namespace zsp {
namespace be {
namespace sw {



class TaskCheckIsExecBlocking :
    public virtual arl::dm::VisitorBase {
public:
    TaskCheckIsExecBlocking(
        dmgr::IDebugMgr     *dmgr,
        bool                imp_target_blocking
    );

    virtual ~TaskCheckIsExecBlocking();

    bool check(arl::dm::ITypeExec *exec);

    bool check(arl::dm::ITypeProcStmt *exec);

    bool check(const std::vector<arl::dm::ITypeExecUP> &execs);

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;

    virtual void visitTypeProcStmtYield(arl::dm::ITypeProcStmtYield *t) override;
    


private:
    static dmgr::IDebug         *m_dbg;
    dmgr::IDebugMgr             *m_dmgr;
    bool                        m_imp_target_blocking;
    bool                        m_blocking;

};

}
}
}


