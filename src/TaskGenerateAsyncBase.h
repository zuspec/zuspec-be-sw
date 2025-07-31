/**
 * TaskGenerateAsyncBase.h
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
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "IGenRefExpr.h"
#include "VisitorBase.h"
#include "ScopeLocalsAssociatedData.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateAsyncBase :
    public virtual VisitorBase {
public:
    TaskGenerateAsyncBase(
        IContext            *ctxt,
        IGenRefExpr         *refgen,
        IOutput             *out,
        const std::string   &fname);

    virtual ~TaskGenerateAsyncBase();

    virtual void visitTypeProcStmtAsyncScope(TypeProcStmtAsyncScope *s) override;

    virtual void visitTypeProcStmtGotoAsyncScope(TypeProcStmtGotoAsyncScope *s) override;

protected:
    virtual void generate(vsc::dm::IAccept *it);

    virtual void enter_stmt(arl::dm::ITypeProcStmt *s);

    virtual void generate_locals(vsc::dm::IDataTypeStruct *locals_t) = 0;

    virtual void generate_init_locals() = 0;

    virtual void init_locals(vsc::dm::IDataTypeStruct *t, int32_t start=0);

protected:
    dmgr::IDebug                            *m_dbg;
    IContext                                *m_ctxt;
    IGenRefExpr                             *m_refgen;
    IOutput                                 *m_out;
    bool                                    m_expr_terminated;
    ScopeLocalsAssociatedData               *m_scope;
    vsc::dm::IDataTypeStruct                *m_largest_locals;
    std::vector<vsc::dm::ITypeVarScope *>   m_scope_s;
    int32_t                                 m_next_scope_id;
    vsc::dm::IDataTypeStruct                *m_locals_t;
    std::string                             m_fname;

};

}
}
}


