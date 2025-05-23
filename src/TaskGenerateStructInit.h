/**
 * TaskGenerateStructInit.h
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
#include "zsp/be/sw/IOutput.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateStructInit : public arl::dm::VisitorBase {
public:
    TaskGenerateStructInit(
        IContext                *ctxt,
        IOutput                 *out_h,
        IOutput                 *out_c);  

    virtual ~TaskGenerateStructInit();
    
    virtual void generate_prefix(vsc::dm::IDataTypeStruct *i);

    virtual void generate_core(vsc::dm::IDataTypeStruct *i);

    virtual void generate(vsc::dm::IDataTypeStruct *i);

    virtual void generate_suffix(vsc::dm::IDataTypeStruct *i);

    virtual void visitDataTypeAddrClaim(arl::dm::IDataTypeAddrClaim *t) override;

    virtual void visitDataTypeArray(vsc::dm::IDataTypeArray *t) override;

    virtual void visitDataTypeBool(vsc::dm::IDataTypeBool *t) override;

    virtual void visitDataTypeEnum(vsc::dm::IDataTypeEnum *t) override;

    virtual void visitDataTypeInt(vsc::dm::IDataTypeInt *t) override;

    virtual void visitDataTypePtr(vsc::dm::IDataTypePtr *t) override;

    virtual void visitDataTypeString(vsc::dm::IDataTypeString *t) override;

    virtual void visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) override;

    virtual void visitTypeField(vsc::dm::ITypeField *f) override;

    virtual void visitTypeFieldRegGroup(arl::dm::ITypeFieldRegGroup *f) override;

protected:
    dmgr::IDebug                *m_dbg;
    vsc::dm::ITypeField         *m_field;
    int32_t                     m_depth;
    IContext                    *m_ctxt;    
    IOutput                     *m_out_h;
    IOutput                     *m_out_c;

};

}
}
}
