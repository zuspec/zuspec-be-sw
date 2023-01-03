/**
 * TaskGenerateFuncProtoEmbeddedC.h
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateFuncProtoEmbeddedC : public virtual arl::dm::VisitorBase {
public:
    TaskGenerateFuncProtoEmbeddedC(NameMap *name_m);

    virtual ~TaskGenerateFuncProtoEmbeddedC();

    void generate(
        IOutput                         *out_decl,
        arl::dm::IDataTypeFunction      *func);

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

private:
    NameMap                                 *m_name_m;
    IOutput                                 *m_out;
};

}
}
}


