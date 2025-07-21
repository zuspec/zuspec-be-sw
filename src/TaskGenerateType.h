/**
 * TaskGenerateType.h
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
#include <unordered_set>
#include "dmgr/IDebugMgr.h"
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/IContext.h"
#include "zsp/arl/dm/IDataTypeComponent.h"
#include "zsp/arl/dm/IDataTypeAction.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IContext.h"
#include "TaskBuildStaticCompTreeMap.h"
#include "TaskCollectAddrTraitTypes.h"
#include "TaskCountAspaceInstances.h"


namespace zsp {
namespace be {
namespace sw {



class TaskGenerateType :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateType(
        IContext    *ctxt,
        IOutput     *out_h,
        IOutput     *out_c);

    virtual ~TaskGenerateType();

    void generate(vsc::dm::IDataTypeStruct *type_t);

    virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) override;

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

    virtual void visitDataTypeArlStruct(arl::dm::IDataTypeArlStruct *t) override;

private:
    static dmgr::IDebug                 *m_dbg;
    IContext                            *m_ctxt;    
    IOutput                             *m_out_c;
    IOutput                             *m_out_h;
};

}
}
}


