/**
 * TaskGenerateExecModelDefineType.h
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

class TaskGenerateExecModelDefineType :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecModelDefineType(
        TaskGenerateExecModel       *gen,
        IOutput                     *out_h,
        IOutput                     *out_c
    );

    virtual ~TaskGenerateExecModelDefineType();

    virtual void generate(vsc::dm::IDataType *item);

    virtual void generate_dflt(vsc::dm::IDataType *item);

	virtual void visitDataTypeAction(arl::dm::IDataTypeAction *i) override;

    virtual void visitDataTypeActivity(arl::dm::IDataTypeActivity *t) override;

	virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

	virtual void visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) override;

    virtual void visitDataTypeRegGroup(arl::dm::IDataTypeRegGroup *t) override;

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

private:
    static dmgr::IDebug             *m_dbg;
    TaskGenerateExecModel           *m_gen;
    IOutput                         *m_out_h;
    IOutput                         *m_out_c;

};

}
}
}


