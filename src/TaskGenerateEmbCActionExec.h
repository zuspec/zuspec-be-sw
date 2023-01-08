/**
 * TaskGenerateEmbCActionExec.h
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
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/IDataTypeAction.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "zsp/be/sw/IOutput.h"
#include "NameMap.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateEmbCActionExec : public arl::dm::VisitorBase {
public:
    TaskGenerateEmbCActionExec(
        dmgr::IDebugMgr             *dmgr,
        NameMap                     *name_m,
        IOutput                     *out_c);

    virtual ~TaskGenerateEmbCActionExec();

    void generate(
        arl::dm::IDataTypeAction    *action_t);

	virtual void visitTypeExecProc(arl::dm::ITypeExecProc *e) override;

private:
    static dmgr::IDebug                         *m_dbg;
    NameMap                                     *m_name_m;
    IOutput                                     *m_out_c;
    std::vector<arl::dm::ITypeExecProc *>       m_execs;

};

}
}
}


