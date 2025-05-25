/**
 * TaskGenerateComp.h
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
#include <unordered_set>
#include "dmgr/IDebugMgr.h"
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/IDataTypeComponent.h"
#include "zsp/arl/dm/IDataTypeAction.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "OutputStr.h"
#include "TaskGenerateStruct.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;


class TaskGenerateComp : 
    public virtual TaskGenerateStruct {
public:
    TaskGenerateComp(
        IContext        *ctxt,
        TypeInfo        *info,
        IOutput         *out_h,
        IOutput         *out_c);

    virtual ~TaskGenerateComp();

//    void generate(arl::dm::IDataTypeComponent *comp_t);

    virtual void generate_init(
        vsc::dm::IDataTypeStruct *t, 
        IOutput                 *out_h,
        IOutput                 *out_c) override;

    virtual void generate_type(
        vsc::dm::IDataTypeStruct    *t, 
        IOutput                     *out_h,
        IOutput                     *out_c) override;

    virtual void generate_data_type(vsc::dm::IDataTypeStruct *t, IOutput *out) override;

    virtual void generate_exec_blocks(vsc::dm::IDataTypeStruct *t, IOutput *out) override;

//	virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

    virtual const char *default_base_header() const { return "zsp_component.h"; }

private:
    enum class Mode {
        FwdDecl,
        Decl
    };

private:
    static dmgr::IDebug                         *m_dbg;
    Mode                                        m_mode;
    std::unordered_set<vsc::dm::IDataType *>    m_decl_s;

};

}
}
}


