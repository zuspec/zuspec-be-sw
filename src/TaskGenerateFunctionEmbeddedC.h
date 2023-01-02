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
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateFunctionEmbeddedC : public arl::dm::VisitorBase {
public:
    TaskGenerateFunctionEmbeddedC(NameMap *name_m);

    virtual ~TaskGenerateFunctionEmbeddedC();

    void generate(
        IOutput                         *out_decl,
        IOutput                         *out_def,
        arl::dm::IDataTypeFunction      *func);

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

	virtual void visitTypeProcStmtAssign(arl::dm::ITypeProcStmtAssign *s) override;

	virtual void visitTypeProcStmtBreak(arl::dm::ITypeProcStmtBreak *s) override;

	virtual void visitTypeProcStmtContinue(arl::dm::ITypeProcStmtContinue *s) override;

	virtual void visitTypeProcStmtForeach(arl::dm::ITypeProcStmtForeach *s) override;

	virtual void visitTypeProcStmtIfElse(arl::dm::ITypeProcStmtIfElse *s) override;

	virtual void visitTypeProcStmtMatch(arl::dm::ITypeProcStmtMatch *s) override;

	virtual void visitTypeProcStmtRepeat(arl::dm::ITypeProcStmtRepeat *s) override;

	virtual void visitTypeProcStmtRepeatWhile(arl::dm::ITypeProcStmtRepeatWhile *s) override;

	virtual void visitTypeProcStmtReturn(arl::dm::ITypeProcStmtReturn *s) override;

	virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) override;

	virtual void visitTypeProcStmtVarDecl(arl::dm::ITypeProcStmtVarDecl *s) override;

	virtual void visitTypeProcStmtWhile(arl::dm::ITypeProcStmtWhile *s) override;

private:
    NameMap                     			        *m_name_m;
    IOutput                     			        *m_out;
    bool                        			        m_is_proto;
    bool                        			        m_gen_decl;
    uint32_t                    			        m_scope_depth;
	std::vector<arl::dm::ITypeProcStmtScope *>		m_scope_s;
};

}
}
}


