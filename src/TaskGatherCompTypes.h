/**
 * TaskGatherCompTypes.h
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
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IContext.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGatherCompTypes :
    public virtual arl::dm::VisitorBase {
public:
    TaskGatherCompTypes(IContext *ctxt);

    virtual ~TaskGatherCompTypes();

    virtual void gather(
        arl::dm::IDataTypeComponent                 *pss_top,
        std::vector<arl::dm::IDataTypeComponent *>  &comp_types);

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual void visitTypeField(vsc::dm::ITypeField *t) override;

private:
    static dmgr::IDebug                                 *m_dbg;
    IContext                                            *m_ctxt;
    std::unordered_set<arl::dm::IDataTypeComponent *>   m_processed;
    std::vector<arl::dm::IDataTypeComponent *>          *m_comp_types; 

};

}
}
}


