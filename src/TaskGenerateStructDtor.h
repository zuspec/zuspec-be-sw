/**
 * TaskGenerateStructDtor.h
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

class TaskGenerateStructDtor :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateStructDtor(
        IContext     *gen,
        IOutput      *out);

    virtual ~TaskGenerateStructDtor();

    void generate_enter(vsc::dm::IDataTypeStruct *t);

    void generate(vsc::dm::IDataTypeStruct *t);

    void generate_leave(vsc::dm::IDataTypeStruct *t);

    virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) override;

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual void visitDataTypeFlowObj(arl::dm::IDataTypeFlowObj *t) override;

    virtual void visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) override;

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

    virtual void visitTypeFieldAddrClaim(arl::dm::ITypeFieldAddrClaim *f) override;
    
    virtual void visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) override;

    virtual void visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) override;

private:
    dmgr::IDebug                *m_dbg;
    IContext                    *m_ctxt;
    IOutput                     *m_out;
    vsc::dm::ITypeField         *m_field;
    bool                        m_field_ref;
};

}
}
}
