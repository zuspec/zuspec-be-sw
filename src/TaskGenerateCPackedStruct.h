/**
 * TaskGenerateCPackedStruct.h
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
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IContext.h"
#include "NameMap.h"
#include "Output.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateCPackedStruct : public virtual arl::dm::VisitorBase {
public:
    TaskGenerateCPackedStruct(IContext *ctxt);

    virtual ~TaskGenerateCPackedStruct();

    void generate(
        Output                          *out,
        arl::dm::IDataTypePackedStruct  *t);

	virtual void visitDataTypeBool(vsc::dm::IDataTypeBool *t) override;

	virtual void visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) override;

	virtual void visitDataTypeInt(vsc::dm::IDataTypeInt *t) override;

	virtual void visitDataTypePackedStruct(arl::dm::IDataTypePackedStruct *t) override;

	virtual void visitTypeFieldPhy(vsc::dm::ITypeFieldPhy *f) override;

private:
    static dmgr::IDebug             *m_dbg;
    IContext                        *m_ctxt;
    Output                          *m_out;
    int32_t                         m_bits;
    int32_t                         m_width;
    std::string                     m_int_t;

};

}
}
}


