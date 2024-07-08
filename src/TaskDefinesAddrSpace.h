/**
 * TaskDefinesAddrSpace.h
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
#include "zsp/arl/dm/impl/VisitorBase.h"

namespace zsp {
namespace be {
namespace sw {



class TaskDefinesAddrSpace :
    public virtual arl::dm::VisitorBase {
public:

    virtual ~TaskDefinesAddrSpace() { }

    bool check(arl::dm::IDataTypeComponent *c) {
        m_has = false;
        for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
            it=c->getFields().begin();
            it!=c->getFields().end(); it++) {
            (*it)->accept(m_this);
        }
        return m_has;
    }

    virtual void visitDataTypeAddrSpaceC(arl::dm::IDataTypeAddrSpaceC *t) {
        m_has = true;
    }

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) { }

    virtual void visitTypeExec(arl::dm::ITypeExec *t) { }


private:
    bool                m_has;
};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


