/*
 * TestExecutorActionQueueBuilder.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, Gsoftware 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author:
 */
#include <vector>
#include "ArlImpl.h"
#include "arl/IContext.h"
#include "TaskBuildExecutorActionQueues.h"
#include "TestExecutorActionQueueBuilder.h"


namespace arl {
namespace be {
namespace sw {


TestExecutorActionQueueBuilder::TestExecutorActionQueueBuilder() {

}

TestExecutorActionQueueBuilder::~TestExecutorActionQueueBuilder() {

}

TEST_F(TestExecutorActionQueueBuilder, smoke) {
    std::vector<arl::IModelActivityUP>      activities_u;
    std::vector<arl::IModelActivity *>      activities;
    std::vector<arl::IModelFieldActionUP>   actions;

    for (uint32_t i=0; i<16; i++) {
        IModelFieldAction *action = m_arl_ctxt->mkModelFieldActionRoot("a", 0);
        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_arl_ctxt->mkModelActivityTraverse(
            action,
            0);
        activities_u.push_back(IModelActivityUP(t));
        activities.push_back(t);
    }

    std::vector<ExecutorActionQueue> queues;
    TaskBuildExecutorActionQueues({}, -1).build(
        queues,
        activities
    );

    ASSERT_EQ(queues.size(), 1);
    ASSERT_EQ(queues[0].size(), 16);
}

TEST_F(TestExecutorActionQueueBuilder, seq_alt_executors) {
    std::vector<arl::IModelActivityUP>      activities_u;
    std::vector<arl::IModelActivity *>      activities;
    std::vector<arl::IModelFieldActionUP>   actions;

    for (uint32_t i=0; i<16; i++) {
        IModelFieldAction *action = m_arl_ctxt->mkModelFieldActionRoot("a", 0);
        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_arl_ctxt->mkModelActivityTraverse(
            action,
            0);
        activities_u.push_back(IModelActivityUP(t));
        activities.push_back(t);
    }

    std::vector<ExecutorActionQueue> queues;
    TaskBuildExecutorActionQueues({}, -1).build(
        queues,
        activities
    );

    ASSERT_EQ(queues.size(), 1);
    ASSERT_EQ(queues[0].size(), 16);
}

}
}
}
