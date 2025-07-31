/**
 * ScopeLocalsAssociatedData.h
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
#include "vsc/dm/IAssociatedData.h"
#include "vsc/dm/IDataTypeStruct.h"
#include "vsc/dm/ITypeVarScope.h"

namespace zsp {
namespace be {
namespace sw {



class ScopeLocalsAssociatedData :
    public virtual vsc::dm::IAssociatedData {
public:
    ScopeLocalsAssociatedData(
        vsc::dm::IDataTypeStruct                    *type,
        const std::vector<vsc::dm::ITypeVarScope *> &scopes,
        bool                                        new_scope=false) : 
        m_type(type), m_scopes(scopes.begin(), scopes.end()),
        m_new_scope(new_scope)  { }

    virtual ~ScopeLocalsAssociatedData() { }

    vsc::dm::IDataTypeStruct *type() const { return m_type; }

    const std::vector<vsc::dm::ITypeVarScope *> &scopes() const { return m_scopes; }

    bool new_scope() const { return m_new_scope; }

private:
    vsc::dm::IDataTypeStruct                *m_type;
    std::vector<vsc::dm::ITypeVarScope *>   m_scopes;
    bool                                    m_new_scope;

};

}
}
}


