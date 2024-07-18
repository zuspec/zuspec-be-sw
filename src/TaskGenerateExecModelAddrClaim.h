/**
 * TaskGenerateExecModelAddrClaim.h
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
#include "zsp/arl/dm/IDataTypeAddrClaim.h"
#include "zsp/be/sw/IOutput.h"
#include "TaskGenerateExecModelStruct.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExecModelAddrClaim : 
    public virtual TaskGenerateExecModelStruct {
public:
    TaskGenerateExecModelAddrClaim(
        TaskGenerateExecModel       *gen,
        IOutput                     *out_h,
        IOutput                     *out_c
    );

    virtual ~TaskGenerateExecModelAddrClaim();

    virtual void generate_type(vsc::dm::IDataTypeStruct *t);

protected:

};

}
}
}


