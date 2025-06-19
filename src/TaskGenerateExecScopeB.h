/**
 * TaskGenerateExecScopeB.h
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
#include "zsp/be/sw/IOutput.h"
#include "IGenRefExpr.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExecScopeB :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecScopeB(
        TaskGenerateExecModel       *gen,
        IGenRefExpr                 *refgen,
        IOutput                     *out_h,
        IOutput                     *out_c);

    virtual ~TaskGenerateExecScopeB();

    virtual void generate(arl::dm::ITypeProcStmtScope *t);

    virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *t) override;

    virtual void visitTypeProcStmtYield(arl::dm::ITypeProcStmtYield *t) override;

private:
    static dmgr::IDebug             *m_dbg;
    TaskGenerateExecModel           *m_gen;
    IGenRefExpr                     *m_refgen;
    IOutput                         *m_out_h;
    IOutput                         *m_out_c;
    std::vector<IOutput *>          m_out_c_s;
    std::vector<IOutput *>          m_out_h_s;
    int32_t                         m_idx;
    int32_t                         m_depth;

};

}
}
}


