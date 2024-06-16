/**
 * TaskGenerateExecModelComponent.h
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

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;


class TaskGenerateExecModelComponent : public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecModelComponent(TaskGenerateExecModel *gen);

    virtual ~TaskGenerateExecModelComponent();

    void generate(arl::dm::IDataTypeComponent *comp_t);

	virtual void visitDataTypeComponent(arl::dm::IDataTypeComponent *t) override;

private:
    enum class Mode {
        FwdDecl,
        Decl
    };

private:
    static dmgr::IDebug                         *m_dbg;
    TaskGenerateExecModel                       *m_gen;
    IOutput                                     *m_out_c;
    IOutput                                     *m_out_h;
    IOutput                                     *m_out_h_prv;
    Mode                                        m_mode;
    std::unordered_set<vsc::dm::IDataType *>    m_decl_s;

};

}
}
}


