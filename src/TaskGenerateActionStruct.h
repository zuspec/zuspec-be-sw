/**
 * TaskGenerateActionStruct.h
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
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "TaskGenerateStructStruct.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateActionStruct : 
    public virtual TaskGenerateStructStruct {
public:
    TaskGenerateActionStruct(
        IContext       *ctxt,
        TypeInfo       *type_info,
        IOutput        *out_h);

    virtual ~TaskGenerateActionStruct();

    void generate(arl::dm::IDataTypeAction *action_t);

    virtual void visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) override;

protected:


};

}
}
}


