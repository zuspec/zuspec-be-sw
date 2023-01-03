/**
 * TaskGenerateEmbCDataType.h
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


class TaskGenerateEmbCDataType : public arl::dm::VisitorBase {
public:
    TaskGenerateEmbCDataType(
        IOutput                 *out,
        NameMap                 *name_m);

    virtual ~TaskGenerateEmbCDataType();

    void generate(vsc::dm::IDataType *type);

	virtual void visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) override;

	virtual void visitDataTypeInt(vsc::dm::IDataTypeInt *t) override;

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

private:
    IOutput                     *m_out;
    NameMap                     *m_name_m;

};

}
}
}

