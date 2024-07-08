/**
 * TaskGenerateExecModelCompExecInit.h
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
#include "zsp/be/sw/IOutput.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExecModelCompExecInit :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecModelCompExecInit(
        TaskGenerateExecModel       *gen,
        IOutput                     *out);

    virtual ~TaskGenerateExecModelCompExecInit();

    void generate (arl::dm::IDataTypeComponent *t);

    virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) override { }

    virtual void visitDataTypeAddrSpaceC(arl::dm::IDataTypeAddrSpaceC *t) override;

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override { } 

    virtual void visitTypeConstraintBlock(vsc::dm::ITypeConstraintBlock *t) override { }

    virtual void visitTypeExec(arl::dm::ITypeExec *t) override { }

    virtual void visitTypeFieldPool(arl::dm::ITypeFieldPool *t) override { }

    virtual void visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *t) override;


private:
    enum Phase {
        UpdateAspace,
        ExecInit
    };

private:
    static dmgr::IDebug             *m_dbg;
    TaskGenerateExecModel           *m_gen;
    IOutput                         *m_out;
    vsc::dm::ITypeField             *m_field;
    Phase                           m_phase;

};

}
}
}


