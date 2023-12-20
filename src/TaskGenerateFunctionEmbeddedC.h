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
#include "dmgr/IDebugMgr.h"
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateFunctionEmbeddedC : public arl::dm::VisitorBase {
public:
    TaskGenerateFunctionEmbeddedC(IContext *ctxt);

    virtual ~TaskGenerateFunctionEmbeddedC();

    void generate(
        IOutput                         *out_def,
        arl::dm::IDataTypeFunction      *func);

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

	virtual void visitTypeProcStmtExpr(arl::dm::ITypeProcStmtExpr *s) override;

private:
    static dmgr::IDebug                             *m_dbg;
    IContext                                        *m_ctxt;
    IOutput                     			        *m_out;
    bool                        			        m_gen_decl;
    uint32_t                    			        m_scope_depth;
};

}
}
}


