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
#include "arl/be/sw/IOutput.h"
#include "arl/impl/VisitorBase.h"
#include "vsc/ITypeExpr.h"
#include "NameMap.h"

namespace arl {
namespace be {
namespace sw {


class TaskGenerateEmbCExpr : public VisitorBase {
public:
    TaskGenerateEmbCExpr(NameMap *name_m);

    virtual ~TaskGenerateEmbCExpr();

    void generate(
        IOutput             *out,
        vsc::ITypeField     *type_scope,
        ITypeProcStmtScope  *proc_scope,
        vsc::ITypeExpr      *expr);

	virtual void visitTypeExprBin(vsc::ITypeExprBin *e) override;

	virtual void visitTypeExprFieldRef(vsc::ITypeExprFieldRef *e) override;

	virtual void visitTypeExprRange(vsc::ITypeExprRange *e) override;

	virtual void visitTypeExprRangelist(vsc::ITypeExprRangelist *e) override;

	virtual void visitTypeExprVal(vsc::ITypeExprVal *e) override;

private:
    NameMap             *m_name_m;
    IOutput             *m_out;
    vsc::ITypeField     *m_type_scope;
    ITypeProcStmtScope  *m_proc_scope;


};

}
}
}


