/**
 * TaskBuildTypeInfo.h
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
#include <set>
#include <vector>
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "vsc/dm/IDataTypeStruct.h"
#include "zsp/be/sw/IContext.h"
#include "TypeInfo.h"

namespace zsp {
namespace be {
namespace sw {

class TaskBuildTypeInfo :
    public virtual arl::dm::VisitorBase {
public:
    TaskBuildTypeInfo(IContext *ctxt);

    virtual ~TaskBuildTypeInfo();

    TypeInfo *build(vsc::dm::IDataTypeStruct *t);

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

    virtual void visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) override;

    virtual void visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) override; 


private:
    static dmgr::IDebug     *m_dbg;
    IContext                *m_ctxt;
    int32_t                 m_depth; 
    TypeInfoUP              m_type_info;
    bool                    m_is_ref;    
    std::set<std::string>   m_field_names;

};

}
}
}


