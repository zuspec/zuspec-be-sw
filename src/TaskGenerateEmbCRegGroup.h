/**
 * TaskGenerateEmbCRegGroup.h
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
#include "zsp/arl/dm/IDataTypeRegGroup.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IOutput.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateEmbCRegGroup : public virtual arl::dm::VisitorBase {
public:
    TaskGenerateEmbCRegGroup(
        IContext            *ctxt,
        IOutput             *out
    );

    virtual ~TaskGenerateEmbCRegGroup();

    void generate(arl::dm::IDataTypeRegGroup *t);

	virtual void visitDataTypeBool(vsc::dm::IDataTypeBool *t) override;

	virtual void visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) override;

	virtual void visitDataTypeInt(vsc::dm::IDataTypeInt *t) override;

	virtual void visitDataTypeString(vsc::dm::IDataTypeString *t) override;

	virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

	virtual void visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) override;

	virtual void visitTypeFieldReg(arl::dm::ITypeFieldReg *f) override;

private:
    static dmgr::IDebug                     *m_dbg;
    IContext                                *m_ctxt;
    IOutput                                 *m_out;
    int32_t                                 m_bitsz;
    vsc::dm::IDataType                      *m_struct_t;
    int32_t                                 m_next_offset;
    std::vector<arl::dm::ITypeFieldReg *>   m_fields;

};

}
}
}


