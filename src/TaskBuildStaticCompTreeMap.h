/**
 * TaskBuildStaticCompTreeMap.h
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
#include <map>
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/impl/VisitorBase.h"

namespace zsp {
namespace be {
namespace sw {



class TaskBuildStaticCompTreeMap :
    public virtual arl::dm::VisitorBase {
public:
    using SubInstM=std::map<arl::dm::IDataTypeComponent *, std::vector<int32_t>>;
    using CompTreeM=std::map<arl::dm::IDataTypeComponent *, SubInstM>;
public:
    TaskBuildStaticCompTreeMap(dmgr::IDebugMgr *dmgr);

    virtual ~TaskBuildStaticCompTreeMap();

    CompTreeM build(arl::dm::IDataTypeComponent *comp_t);

    virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) override { }

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual void visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *t) override {
        t->getDataType()->accept(m_this);
    }

    virtual void visitTypeFieldRef(vsc::dm::ITypeFieldRef *t) override { }

private:
    static dmgr::IDebug                 *m_dbg;

    // Maintain data on a per-comp-type basis

    // Each component type has a certain number of total instances underneath
    // Each component type has a map of comp_type -> available offsets
    struct CompData {
        arl::dm::IDataTypeComponent                                         *type;
        int32_t                                                             num_comp;
        std::map<arl::dm::IDataTypeComponent *, std::vector<int32_t>>       sub_comp_m;
    };

    int32_t                                                                 m_num_comp;
    std::map<arl::dm::IDataTypeComponent *, CompData>                       m_comp_data;
    std::vector<CompData *>                                                 m_comp_s;

};

}
}
}


