/**
 * TaskGatherTypes.h
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
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "vsc/dm/IDataTypeStruct.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IContext.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGatherTypes :
    public virtual arl::dm::VisitorBase {
public:
    TaskGatherTypes(IContext *ctxt);

    virtual ~TaskGatherTypes();

    virtual void gather(vsc::dm::IAccept *item);

    const std::vector<vsc::dm::IDataTypeStruct *> &types() const {
        return m_types;
    }

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

    virtual void visitDataTypeArlStruct(arl::dm::IDataTypeArlStruct *t) override;

    virtual void visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) override;


private:
    static dmgr::IDebug                             *m_dbg;
    IContext                                        *m_ctxt;
    std::vector<vsc::dm::IDataTypeStruct *>         m_types;
    std::unordered_set<vsc::dm::IDataTypeStruct *>  m_types_s;

};

}
}
}


