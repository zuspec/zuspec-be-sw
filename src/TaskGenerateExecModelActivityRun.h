/**
 * TaskGenerateExecModelActivityRun.h
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
#include "OutputExecScope.h"

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExecModelActivityRun :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecModelActivityRun(
        TaskGenerateExecModel       *gen,
        IOutput                     *out
    );

    virtual ~TaskGenerateExecModelActivityRun();

    void generate(arl::dm::IDataTypeActivity *activity);

	virtual void visitDataTypeActivitySequence(arl::dm::IDataTypeActivitySequence *t) override;

	virtual void visitDataTypeActivityTraverse(arl::dm::IDataTypeActivityTraverse *t) override;

	virtual void visitDataTypeActivityTraverseType(arl::dm::IDataTypeActivityTraverseType *t) override;

private:
    static dmgr::IDebug                                 *m_dbg;
    TaskGenerateExecModel                               *m_gen;
    IOutput                                             *m_out;
    std::vector<arl::dm::IDataTypeActivityScope *>      m_scope_s;
    std::vector<OutputExecScope>                        m_out_s;

};

}
}
}


