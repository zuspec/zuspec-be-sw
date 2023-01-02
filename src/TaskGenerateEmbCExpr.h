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
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "vsc/dm/ITypeExpr.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {


class TaskGenerateEmbCExpr : public arl::dm::VisitorBase {
public:
    TaskGenerateEmbCExpr(NameMap *name_m);

    virtual ~TaskGenerateEmbCExpr();

    void generate(
        IOutput                         *out,
        vsc::dm::ITypeField             *type_scope,
        arl::dm::ITypeProcStmtScope     *proc_scope,
        vsc::dm::ITypeExpr              *expr);

	virtual void visitTypeExprBin(vsc::dm::ITypeExprBin *e) override;

	virtual void visitTypeExprFieldRef(vsc::dm::ITypeExprFieldRef *e) override;

	virtual void visitTypeExprRange(vsc::dm::ITypeExprRange *e) override;

	virtual void visitTypeExprRangelist(vsc::dm::ITypeExprRangelist *e) override;

	virtual void visitTypeExprVal(vsc::dm::ITypeExprVal *e) override;

private:
    NameMap                         *m_name_m;
    IOutput                         *m_out;
    vsc::dm::ITypeField             *m_type_scope;
    arl::dm::ITypeProcStmtScope     *m_proc_scope;


};

}
}
}


