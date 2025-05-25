/**
 * TaskGenerateCompDoInit.h
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
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"
#include "TypeInfo.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateCompDoInit :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateCompDoInit(
        IContext                *ctxt,
        TypeInfo                *info,
        IOutput                 *out_h,
        IOutput                 *out_c);

    virtual ~TaskGenerateCompDoInit();

    virtual void generate(vsc::dm::IDataTypeStruct *t);

    virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual void visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) override;

    virtual void visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) override;

private:
    IContext                *m_ctxt;
    TypeInfo                *m_info;
    IOutput                 *m_out_h;
    IOutput                 *m_out_c;
    int32_t                 m_depth;
    vsc::dm::ITypeField     *m_field;
    bool                    m_is_ref;

};

}
}
}


