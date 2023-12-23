/**
 * TaskGetExecScopeVarInfo.h
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

namespace zsp {
namespace be {
namespace sw {



class TaskGetExecScopeVarInfo : arl::dm::VisitorBase {
public:

    virtual ~TaskGetExecScopeVarInfo() { }


    ExecScopeVarInfo get(vsc::dm::IAccept *scope, int32_t var_off) {
        m_var_off = var_off;
        m_var = 0;
        m_flags = ExecScopeVarFlags::NoFlags;
        scope->accept(m_this);
        return {.var=m_var, .flags=m_flags};
    }

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override {
        m_var = t->getParamScope()->getVariables().at(m_var_off).get();
        m_var->getDataType()->accept(m_this);
    }

	virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) override {
        m_var = s->getVariables().at(m_var_off).get();
    }

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override {
        m_flags = (m_flags | ExecScopeVarFlags::IsPtr);
    }

private:
    int32_t                             m_var_off;
    arl::dm::ITypeProcStmtVarDecl       *m_var;
    ExecScopeVarFlags                   m_flags;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


