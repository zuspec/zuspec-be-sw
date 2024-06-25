/**
 * TaskGenerateExecModelCountBlockingScopes.h
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

namespace zsp {
namespace be {
namespace sw {

class TaskGenerateExecModel;

class TaskGenerateExecModelCountBlockingScopes :
    public virtual arl::dm::VisitorBase {
public:
    TaskGenerateExecModelCountBlockingScopes(
        TaskGenerateExecModel *gen
    );

    virtual ~TaskGenerateExecModelCountBlockingScopes();

    int32_t count(arl::dm::IDataTypeActivity *t);

	virtual void visitDataTypeActivityParallel(arl::dm::IDataTypeActivityParallel *t) override;

	virtual void visitDataTypeActivityReplicate(arl::dm::IDataTypeActivityReplicate *t) override;

	virtual void visitDataTypeActivitySequence(arl::dm::IDataTypeActivitySequence *t) override;

	virtual void visitDataTypeActivityTraverse(arl::dm::IDataTypeActivityTraverse *t) override;

private:
    static dmgr::IDebug         *m_dbg; 
    TaskGenerateExecModel       *m_gen;
    int32_t                     m_count;
};

}
}
}


