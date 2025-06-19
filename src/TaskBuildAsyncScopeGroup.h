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

	virtual void visitTypeExprBin(vsc::dm::ITypeExprBin *e) override;

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;

	virtual void visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) override;

	virtual void visitTypeProcStmtRepeatWhile(arl::dm::ITypeProcStmtRepeatWhile *s) override;

	virtual void visitTypeProcStmtWhile(arl::dm::ITypeProcStmtWhile *s) override;

	virtual void visitTypeProcStmtYield(arl::dm::ITypeProcStmtYield *s) override;

private:

    TypeProcStmtAsyncScope *currentScope() {
        return m_scopes.at(m_scopes.size()-2).get();
    }

private:
    static dmgr::IDebug                     *m_dbg;
    IContext                                *m_ctxt;
    vsc::dm::ITypeExprUP                    m_expr;
    std::vector<TypeProcStmtAsyncScopeUP>   m_scopes;

};

}
}
}


