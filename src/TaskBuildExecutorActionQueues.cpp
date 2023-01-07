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
#include "zsp/arl/dm/impl/TaskFindExecutor.h"
#include "dmgr/impl/DebugMacros.h"
#include "TaskBuildExecutorActionQueues.h"


namespace zsp {
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
        arl::dm::IModelEvalIterator         *activity_it) {
    DEBUG_ENTER("build");
    m_executor_queues = &executor_queues;

    if (m_executors.size() > 0) {
        for (std::vector<IModelFieldExecutor *>::const_iterator
            it=m_executors.begin();
            it!=m_executors.end(); it++) {
            m_executor_queues->push_back(ExecutorActionQueue());
        }

        if (m_executors.size() > 1) {
            // Cause the primary executor to emit its 'alive' signal
            m_executor_queues->at(m_dflt_executor).push_back(
                {
                    .kind=ExecutorActionQueueEntryKind::Notify,
                    .action_id=1,
                    .executor_id=-1,
                    .action=0
                }
            );

            // Cause all non-primary cores to wait for the primary 
            // core to begin execution
            for (uint32_t i=0; i<m_executors.size(); i++) {
                m_executor_exec_ids.push_back((i==m_dflt_executor)?1:0);
                if (i != m_dflt_executor) {
                    m_executor_queues->at(i).push_back(
                        {
                            .kind=ExecutorActionQueueEntryKind::Depend,
                            .action_id=1,
                            .executor_id=m_dflt_executor,
                            .action=0
                        }
                    );
                }
            }
        }
    } else {
        m_executor_queues->push_back(ExecutorActionQueue());
        m_dflt_executor = 0;
    }

    process_scope(activity_it);

    // TODO: could possibly identify blocking synchronizations as a post-step
    if (m_executors.size() > 1) {
        // Have each non-primary executor notify its completion
        for (uint32_t i=0; i<m_executors.size(); i++) {
            if (i != m_dflt_executor) {
                m_executor_exec_ids[i] += 1;
                m_executor_queues->at(i).push_back(
                    {
                        .kind=ExecutorActionQueueEntryKind::Notify,
                        .action_id=m_executor_exec_ids[i],
                        .executor_id=-1,
                        .action=0
                    }
                );
            }
        }

        // Have the primary executor wait for all non-primary executors
        for (uint32_t i=0; i<m_executors.size(); i++) {
            if (i != m_dflt_executor) {
                m_executor_queues->at(m_dflt_executor).push_back(
                    {
                        .kind=ExecutorActionQueueEntryKind::Depend,
                        .action_id=m_executor_exec_ids[i],
                        .executor_id=static_cast<int32_t>(i),
                        .action=0
                    }
                );
            }
        }
    }

    // Cause all non-primary 
    DEBUG_LEAVE("build");
}

void TaskBuildExecutorActionQueues::visitModelActivityParallel(IModelActivityParallel *a) {

}

void TaskBuildExecutorActionQueues::visitModelActivityTraverse(IModelActivityTraverse *a) {

}

void TaskBuildExecutorActionQueues::process_scope(IModelEvalIterator *s_it) {
    while (s_it->next()) {
        switch (s_it->type()) {
            case arl::dm::ModelEvalNodeT::Action: {
                // TODO: must handle entry/exit of compound action
                process_traverse(s_it->action());
            } break;

            case arl::dm::ModelEvalNodeT::Sequence: {
                process_scope(s_it->iterator());
            } break;

            case arl::dm::ModelEvalNodeT::Parallel: {
                process_parallel(s_it->iterator());
            } break;
        }
    }
}

void TaskBuildExecutorActionQueues::process_parallel(IModelEvalIterator *it) {
    DEBUG_ENTER("process_parallel");
    std::vector<int32_t> last_executor;

    while (it->next()) {
        m_last_executor.push_back(m_last_executor.back());

        switch (it->type()) {
            case arl::dm::ModelEvalNodeT::Action: {
                // TODO: must handle entry/exit of compound action
                if (!it->action()->isCompound()) {
                    process_traverse(it->action());
                } else {
                    // Action is compound. Process scope
                    process_scope(it->iterator());
                }

                // TODO: 
            } break;

            case arl::dm::ModelEvalNodeT::Sequence: {
                process_scope(it->iterator());
            } break;

            case arl::dm::ModelEvalNodeT::Parallel: {
                process_parallel(it->iterator());
            } break;
        }
        
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

    DEBUG_LEAVE("process_parallel");
}

void TaskBuildExecutorActionQueues::process_traverse(IModelFieldAction *a) {
    DEBUG_ENTER("process_traverse");
    int32_t executor = 0; // TODO:

    IModelFieldExecutor *executor_p = TaskFindExecutor().find(a);

    fprintf(stdout, "Executor: %p\n", executor_p);

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

    // TODO: Can't really rely on 'action' sticking around. Must convert to
    //       code that can later be emitted
    m_executor_queues->at(executor).push_back(
        {
            .kind=ExecutorActionQueueEntryKind::Action,
            .action_id=this_action_id,
            .executor_id=-1,
            .action=a
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
    DEBUG_LEAVE("process_traverse");
}

dmgr::IDebug *TaskBuildExecutorActionQueues::m_dbg = 0;

}
}
}
