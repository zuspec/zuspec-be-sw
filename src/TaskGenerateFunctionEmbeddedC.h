/**
 * TaskGenerateFunctionEmbeddedC.h
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
#include "NameMap.h"

namespace arl {
namespace be {
namespace sw {



class TaskGenerateFunctionEmbeddedC : public VisitorBase {
public:
    TaskGenerateFunctionEmbeddedC(NameMap *name_m);

    virtual ~TaskGenerateFunctionEmbeddedC();

    void generate(
        IOutput             *out_decl,
        IOutput             *out_def,
        IDataTypeFunction   *func);

	virtual void visitDataTypeFunction(IDataTypeFunction *t) override;

	virtual void visitTypeProcStmtBreak(ITypeProcStmtBreak *s) override;

	virtual void visitTypeProcStmtContinue(ITypeProcStmtContinue *s) override;

	virtual void visitTypeProcStmtForeach(ITypeProcStmtForeach *s) override;

	virtual void visitTypeProcStmtIfElse(ITypeProcStmtIfElse *s) override;

	virtual void visitTypeProcStmtMatch(ITypeProcStmtMatch *s) override;

	virtual void visitTypeProcStmtRepeat(ITypeProcStmtRepeat *s) override;

	virtual void visitTypeProcStmtRepeatWhile(ITypeProcStmtRepeatWhile *s) override;

	virtual void visitTypeProcStmtReturn(ITypeProcStmtReturn *s) override;

	virtual void visitTypeProcStmtScope(ITypeProcStmtScope *s) override;

	virtual void visitTypeProcStmtVarDecl(ITypeProcStmtVarDecl *s) override;

	virtual void visitTypeProcStmtWhile(ITypeProcStmtWhile *s) override;

private:
    NameMap                     *m_name_m;
    IOutput                     *m_out;
    bool                        m_is_proto;
    bool                        m_gen_decl;
    uint32_t                    m_scope_depth;
};

}
}
}


