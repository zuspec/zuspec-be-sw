/**
 * TaskCountAspaceInstances.h
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
#include "zsp/arl/dm/impl/VisitorBase.h"

namespace zsp {
namespace be {
namespace sw {



class TaskCountAspaceInstances :
    public virtual arl::dm::VisitorBase {
public:

    virtual ~TaskCountAspaceInstances() { }

    int32_t count(arl::dm::IDataTypeComponent *root) {
        m_cache.clear();
        m_count.clear();
        return _count(root);
    }

    int32_t _count(arl::dm::IDataTypeComponent *t) {
        int32_t ret;
        std::map<arl::dm::IDataTypeComponent *, int32_t>::iterator it;

        if ((it=m_cache.find(t)) != m_cache.end()) {
            ret = it->second;
        } else {
            m_count.push_back(0);
            for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
                it=t->getFields().begin();
                it!=t->getFields().end(); it++) {
                (*it)->accept(m_this);
            }
            ret = m_count.back();
            m_count.pop_back();
            m_cache.insert({t, ret});
        }
        return ret;
    }

    virtual void visitDataTypeAddrSpaceC(arl::dm::IDataTypeAddrSpaceC *t) {
        m_count.back() += 1;
    }

private:
    std::map<arl::dm::IDataTypeComponent *, int32_t>     m_cache;
    std::vector<int32_t>                                 m_count;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


