/**
 * TaskGenerateExprNB.h
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
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "IGenRefExpr.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExprNB : public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExprNB(
        IContext                    *ctxt,  
        IGenRefExpr                 *refgen,
        IOutput                     *out
    );

    virtual ~TaskGenerateExprNB();

    virtual void generate(vsc::dm::ITypeExpr *e);

	virtual void visitTypeExprArrIndex(vsc::dm::ITypeExprArrIndex *e) override;

	virtual void visitTypeExprBin(vsc::dm::ITypeExprBin *e) override;

	virtual void visitTypeExprFieldRef(vsc::dm::ITypeExprFieldRef *e) override;

    virtual void visitTypeExprMethodCallContext(arl::dm::ITypeExprMethodCallContext *e) override;

    virtual void visitTypeExprMethodCallStatic(arl::dm::ITypeExprMethodCallStatic *e) override;

	virtual void visitTypeExprRange(vsc::dm::ITypeExprRange *e) override;

	virtual void visitTypeExprRangelist(vsc::dm::ITypeExprRangelist *e) override;

	virtual void visitTypeExprRefBottomUp(vsc::dm::ITypeExprRefBottomUp *e) override;

	virtual void visitTypeExprRefPath(vsc::dm::ITypeExprRefPath *e) override;

	virtual void visitTypeExprRefTopDown(vsc::dm::ITypeExprRefTopDown *e) override;

	virtual void visitTypeExprSubField(vsc::dm::ITypeExprSubField *e) override;

	virtual void visitTypeExprUnary(vsc::dm::ITypeExprUnary *e) override;

	virtual void visitTypeExprVal(vsc::dm::ITypeExprVal *e) override;

protected:
    dmgr::IDebug                    *m_dbg;
    IContext                        *m_ctxt;    
    IGenRefExpr                     *m_refgen;
    IOutput                         *m_out;
    int32_t                         m_depth;

};

}
}
}


