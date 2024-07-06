/**
 * TaskCollectAddrTraitTypes.h
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



class TaskCollectAddrTraitTypes :
    public virtual arl::dm::VisitorBase {
public:
    using TraitM=std::map<vsc::dm::IDataTypeStruct *, int32_t>;
public:

    TaskCollectAddrTraitTypes(dmgr::IDebugMgr *dmgr) { }

    virtual ~TaskCollectAddrTraitTypes() { }

    TraitM collect(arl::dm::IDataTypeComponent *comp_t) {
        m_trait_m.clear();
        comp_t->accept(m_this);
        return m_trait_m;
    }

    virtual void visitDataTypeAction(arl::dm::IDataTypeAction *t) { }

    virtual void visitDataTypeArlStruct(arl::dm::IDataTypeArlStruct *t) { }

    virtual void visitDataTypeAddrSpaceC(arl::dm::IDataTypeAddrSpaceC *t) {
        TraitM::const_iterator it;

        if ((it=m_trait_m.find(t->getTraitType())) == m_trait_m.end()) {
            m_trait_m.insert({t->getTraitType(), m_trait_m.size()});
        }
    }

private:
    TraitM              m_trait_m;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


