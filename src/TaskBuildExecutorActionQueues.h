/**
 * TaskBuildExecutorActionQueues.h
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
#include <vector>
#include "dmgr/IDebug.h"
#include "zsp/arl/dm/IContext.h"
#include "zsp/arl/dm/IModelActivity.h"
#include "zsp/arl/dm/IModelFieldAction.h"
#include "zsp/arl/dm/IModelFieldExecutor.h"
#include "zsp/arl/dm/impl/VisitorBase.h"

using namespace zsp::arl::dm;

namespace zsp {
namespace be {
namespace sw {


struct ExecutorActionQueueParallelEntry;
using ExecutorActionQueueParallelEntryUP=std::unique_ptr<ExecutorActionQueueParallelEntry>;


// Each entry in an executor's queue is either
// - A dependency on another executor's action completion
//   - executor_id
//   - action_id
// - An action traversal
//   - action
//   - action_id
// - An executor-local parallel
//   - handle to parallel structure

enum class ExecutorActionQueueEntryKind {
    Depend,
    Action,
    Parallel
};

struct ExecutorActionQueueEntry {
    ExecutorActionQueueEntryKind            kind;

    int32_t                                 action_id;
    int32_t                                 executor_id;

    IModelFieldAction                       *action;

    // Populated if this entry is a parallel
    ExecutorActionQueueParallelEntryUP      parallel;
};

using ExecutorActionQueueParallelBranch=std::vector<ExecutorActionQueueEntry>;

struct ExecutorActionQueueParallelEntry {
    std::vector<ExecutorActionQueueParallelBranch>  branches;
};

using ExecutorActionQueue=std::vector<ExecutorActionQueueEntry>;


class TaskBuildExecutorActionQueues : public VisitorBase {
public:
    TaskBuildExecutorActionQueues(
        IContext                                        *ctxt,
        const std::vector<IModelFieldExecutor *>        &executors,
        int32_t                                         dflt_executor
    );

    virtual ~TaskBuildExecutorActionQueues();

    void build(
        std::vector<ExecutorActionQueue>    &executor_queues,
        const std::vector<IModelActivity *> &actvities
    );

	virtual void visitModelActivityParallel(IModelActivityParallel *a) override;

	virtual void visitModelActivityTraverse(IModelActivityTraverse *a) override;

private:
    using LastExecutorFrame=std::vector<int32_t>;


private:
    static dmgr::IDebug                         *m_dbg;
    std::vector<IModelFieldExecutor *>          m_executors;
    std::vector<ExecutorActionQueue>            *m_executor_queues;
    std::vector<int32_t>                        m_executor_exec_ids;
    int32_t                                     m_dflt_executor;
    std::vector<LastExecutorFrame>              m_last_executor;

};

}
}
}


