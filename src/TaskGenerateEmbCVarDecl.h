/**
 * TaskGenerateEmbCVarDecl.h
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
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IOutput.h"
#include "NameMap.h"
#include "TaskGenerateEmbCDataType.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateEmbCVarDecl : public arl::dm::VisitorBase {
public:
    TaskGenerateEmbCVarDecl(
        IOutput                 *out,
        NameMap                 *name_m);

    virtual ~TaskGenerateEmbCVarDecl();

    void generate(
        arl::dm::ITypeProcStmt  *stmt);

    void generate(
        vsc::dm::IDataType          *type,
        vsc::dm::ITypeField         *field);

	virtual void visitTypeField(vsc::dm::ITypeField *f) override;

	virtual void visitTypeFieldPool(arl::dm::ITypeFieldPool *f) override;

	virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) override;

	virtual void visitTypeProcStmtVarDecl(arl::dm::ITypeProcStmtVarDecl *s) override;

private:
    IOutput                     *m_out;
    NameMap                     *m_name_m;
    TaskGenerateEmbCDataType    m_dt_gen;
    int32_t                     m_depth;

};

}
}
}


