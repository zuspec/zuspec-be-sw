/**
 * TaskGenerateExecModelFwdDecl.h
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

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExecModelFwdDecl : public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecModelFwdDecl(
        IContext                *ctxt,
        IOutput                 *out);

    virtual ~TaskGenerateExecModelFwdDecl();

    void generate(vsc::dm::IAccept *item);

    void generate_dflt(vsc::dm::IAccept *item);

    virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) override;

    virtual void visitDataTypeActivitySequence(arl::dm::IDataTypeActivitySequence *t) override;

	virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

    virtual void visitTypeExecProc(arl::dm::ITypeExecProc *t) override;

	virtual void visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) override;

private:
    static dmgr::IDebug             *m_dbg;
    IContext                        *m_ctxt;
    IOutput                         *m_out;


};

}
}
}


