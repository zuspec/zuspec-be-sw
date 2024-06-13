/**
 * TaskGenerateExecModel.h
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
#include "zsp/be/sw/IOutput.h"
#include "zsp/arl/dm/IDataTypeComponent.h"
#include "zsp/arl/dm/IDataTypeAction.h"

namespace zsp {
namespace be {
namespace sw {



class TaskGenerateExecModel {
public:
    TaskGenerateExecModel(
        dmgr::IDebugMgr                 *dmgr);

    


    virtual ~TaskGenerateExecModel();

    void generate(
        arl::dm::IDataTypeComponent     *comp_t,
        arl::dm::IDataTypeAction        *action_t,
        std::ostream                    *out_c,
        std::ostream                    *out_h,
        std::ostream                    *out_h_prv);

private:
    static dmgr::IDebug                 *m_dbg;

};

}
}
}


