/**
 * TaskGenerateExecModelAction.h
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
#include "zsp/be/sw/IOutput.h"
#include "IGenRefExpr.h"


namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExecModelAction : public arl::dm::VisitorBase {
public:
    TaskGenerateExecModelAction(
        TaskGenerateExecModel       *gen,
        bool                        is_root=false);

    virtual ~TaskGenerateExecModelAction();

    void generate(arl::dm::IDataTypeAction *action);

	virtual void visitDataTypeAction(arl::dm::IDataTypeAction *i) override;

private:
    
private:
    static dmgr::IDebug             *m_dbg;
    TaskGenerateExecModel           *m_gen;
    bool                            m_is_root;
    int32_t                         m_depth;

};

}
}
}


