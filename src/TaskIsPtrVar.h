/**
 * TaskIsPtrVar.h
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

namespace zsp {
namespace be {
namespace sw {



class TaskIsPtrVar : public virtual arl::dm::VisitorBase {
public:

    virtual ~TaskIsPtrVar() { }

    bool check(arl::dm::ITypeProcStmtVarDecl *v) {
        m_ret = false;
        m_in_param = false;
        v->accept(m_this);
        return m_ret;
    }

	virtual void visitDataTypeFunctionParamDecl(arl::dm::IDataTypeFunctionParamDecl *t) override {
        m_in_param = true;
        t->getDataType()->accept(m_this);
        m_in_param = false;
    }

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override {
        m_ret |= m_in_param;
    }

private:
    bool                m_in_param;
    bool                m_ret;
};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


