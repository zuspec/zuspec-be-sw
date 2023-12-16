/**
 * TaskGenerateEmbCExpr.h
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "vsc/dm/ITypeExpr.h"
#include "ITaskGenerateExpr.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {


class TaskGenerateEmbCExpr : 
    public virtual ITaskGenerateExpr, 
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateEmbCExpr(IContext *ctxt);

    virtual ~TaskGenerateEmbCExpr();
    
    virtual void init(
        vsc::dm::IDataTypeStruct                            *type_scope,
        std::vector<arl::dm::ITypeProcStmtDeclScope *>      *proc_scopes) override {
        m_type_scope = type_scope;
        m_proc_scopes = proc_scopes;
    }

    void generate(
        IOutput                                             *out,
        vsc::dm::ITypeExpr                                  *expr);

    void setBottomUpPref(const std::string &pref, bool ptref) {
        m_bottom_up_pref = pref;
        m_bottom_up_ptref = ptref;
    }

    void setActivePref(const std::string &pref, bool ptref) {
        m_active_pref = pref;
        m_active_ptref = ptref;
    }

	virtual void visitTypeExprBin(vsc::dm::ITypeExprBin *e) override;

	virtual void visitTypeExprFieldRef(vsc::dm::ITypeExprFieldRef *e) override;

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;

	virtual void visitTypeExprRange(vsc::dm::ITypeExprRange *e) override;

	virtual void visitTypeExprRangelist(vsc::dm::ITypeExprRangelist *e) override;

	virtual void visitTypeExprVal(vsc::dm::ITypeExprVal *e) override;

private:
    static dmgr::IDebug                                 *m_dbg;
    IContext                                            *m_ctxt;
    IOutput                                             *m_out;
    vsc::dm::IDataTypeStruct                            *m_type_scope;
    std::vector<arl::dm::ITypeProcStmtDeclScope *>      *m_proc_scopes;
    std::string                                         m_bottom_up_pref;
    bool                                                m_bottom_up_ptref;
    std::string                                         m_active_pref;
    bool                                                m_active_ptref;


};

}
}
}


