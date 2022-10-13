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
#include "TaskBuildExecutorActionQueues.h"


namespace arl {
namespace be {
namespace sw {


TaskBuildExecutorActionQueues::TaskBuildExecutorActionQueues(
    const std::vector<IModelFieldExecutor *>    &executors,
    int32_t                                     dflt_executor) :
    m_executors(executors.begin(), executors.end()), m_dflt_executor(dflt_executor) {

}

TaskBuildExecutorActionQueues::~TaskBuildExecutorActionQueues() {

}

void TaskBuildExecutorActionQueues::build(
        std::vector<ExecutorActionQueue>    &executor_queues,
        const std::vector<IModelActivity *> &actvities) {
    m_executor_queues = &executor_queues;


}

}
}
}
