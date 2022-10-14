/*
 * TaskBuildExecutorActionQueues.cpp
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
#include "arl/impl/TaskFindExecutor.h"
#include "vsc/impl/DebugMacros.h"
#include "TaskBuildExecutorActionQueues.h"


namespace arl {
namespace be {
namespace sw {


TaskBuildExecutorActionQueues::TaskBuildExecutorActionQueues(
    IContext                                    *ctxt,
    const std::vector<IModelFieldExecutor *>    &executors,
    int32_t                                     dflt_executor) :
    m_executors(executors.begin(), executors.end()), m_dflt_executor(dflt_executor) {
    DEBUG_INIT("TaskBuildExecutorActionQueues", ctxt->getDebugMgr());

    m_last_executor.push_back({0});

}

TaskBuildExecutorActionQueues::~TaskBuildExecutorActionQueues() {

}

void TaskBuildExecutorActionQueues::build(
        std::vector<ExecutorActionQueue>    &executor_queues,
        const std::vector<IModelActivity *> &actvities) {
    DEBUG_ENTER("build");
    m_executor_queues = &executor_queues;

    if (m_executors.size() > 0) {
        for (std::vector<IModelFieldExecutor *>::const_iterator
            it=m_executors.begin();
            it!=m_executors.end(); it++) {
            m_executor_queues->push_back(ExecutorActionQueue());
        }
    } else {
        m_executor_queues->push_back(ExecutorActionQueue());
        m_dflt_executor = 0;
    }

    for (std::vector<IModelActivity *>::const_iterator
        it=actvities.begin();
        it!=actvities.end(); it++) {
        (*it)->accept(m_this);
    }
    DEBUG_LEAVE("build");
}

void TaskBuildExecutorActionQueues::visitModelActivityParallel(IModelActivityParallel *a) {
    DEBUG_ENTER("visitModelActivityParallel");
    std::vector<int32_t> last_executor;

    for (std::vector<IModelActivity *>::const_iterator
        it=a->branches().begin();
        it!=a->branches().end(); it++) {

        m_last_executor.push_back(m_last_executor.back());
        (*it)->accept(m_this);
        
        // Merge the resulting 'last-executor' into the list
        // that we're maintaining
        for (LastExecutorFrame::const_iterator
            it=m_last_executor.back().begin();
            it!=m_last_executor.back().end(); it++) {
            bool exist = false;
            for (std::vector<int32_t>::const_iterator
                it_l=last_executor.begin();
                it_l!=last_executor.end(); it_l++) {
                if (*it == *it_l) {
                    exist = true;
                    break;
                }
            }
            if (!exist) {
                last_executor.push_back(*it);
            }
        }
        m_last_executor.pop_back(); 
    }

    // Replace the incoming last-executor with the result
    // from this
    m_last_executor.back().clear();
    m_last_executor.back().insert(
        m_last_executor.back().begin(), 
        last_executor.begin(), 
        last_executor.end());

    DEBUG_LEAVE("visitModelActivityParallel");
}

void TaskBuildExecutorActionQueues::visitModelActivityTraverse(IModelActivityTraverse *a) {
    DEBUG_ENTER("visitModelActivityTraverse");
    int32_t executor = 0; // TODO:

    IModelFieldExecutor *executor_p = TaskFindExecutor().find(a->getTarget());

    if (executor_p) {
        // Search to find the index
        for (uint32_t i=0; i<m_executors.size(); i++) {
            if (m_executors.at(i) == executor_p) {
                executor = i;
                break;
            }
        }
    } else {
        executor = m_dflt_executor; 
    }

    DEBUG("executor: %d", executor);

    if (m_last_executor.back().size() > 1) {
        // TODO:
    } else {
        // Need to add a synchronization request
        if (m_last_executor.back().at(0) != executor) {
            int32_t dep_executor=m_last_executor.back().at(0);
            DEBUG("Action execution depends on %d\n", dep_executor);

            // The action ID is in the last entry on that queue
            int32_t dep_action_id=m_executor_queues->at(dep_executor).back().action_id;

            m_executor_queues->at(executor).push_back(
                {
                    .kind=ExecutorActionQueueEntryKind::Depend,
                    .action_id=dep_action_id,
                    .executor_id=m_last_executor.back().at(0)
                }
            );
        }
    }

    // TODO: must consider 'last executor' to be both
    // hierarchical and multi-value (eg last from all branches of a parallel)
//    if (executor != m_last_executor.back()) {
        // TODO: add a synchronizer on this executor
//    }

    int32_t this_action_id = m_executor_queues->at(executor).size()+1;

    m_executor_queues->at(executor).push_back(
        {
            .kind=ExecutorActionQueueEntryKind::Action,
            .action_id=this_action_id,
            .executor_id=-1,
            .action=a->getTarget()
        }
    );

    // A multi-executor preceeding is replaced with
    // a single last-executor
    if (m_last_executor.back().size() > 1) {
        m_last_executor.back().clear();
        m_last_executor.back().push_back(executor);
    } else {
        m_last_executor.back().at(0) = executor;
    }
    DEBUG_LEAVE("visitModelActivityTraverse");
}

vsc::IDebug *TaskBuildExecutorActionQueues::m_dbg = 0;

}
}
}
