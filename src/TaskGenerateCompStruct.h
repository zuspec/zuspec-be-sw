/**
 * TaskGenerateCompStruct.h
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
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "TaskGenerateStructStruct.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateCompStruct : 
    public virtual TaskGenerateStructStruct {
public:
    TaskGenerateCompStruct(
        IContext   *gen,
        TypeInfo   *info,
        IOutput    *out);

    virtual ~TaskGenerateCompStruct();

    virtual const char *default_base_type() const { return "zsp_component_t"; }

    virtual void generate_suffix(vsc::dm::IDataTypeStruct *i) override;

    virtual void generate_dtor(vsc::dm::IDataTypeStruct *i) override { }

    virtual void visitDataTypeAddrSpaceTransparentC(arl::dm::IDataTypeAddrSpaceTransparentC *t) override;

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;


};

}
}
}


