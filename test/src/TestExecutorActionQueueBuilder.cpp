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
#include "zsp/arl/dm/impl/ModelBuildContext.h"
#include "TaskBuildExecutorActionQueues.h"
#include "TestExecutorActionQueueBuilder.h"

using namespace zsp::arl::dm;
using namespace vsc::dm;

namespace zsp {
namespace be {
namespace sw {


TestExecutorActionQueueBuilder::TestExecutorActionQueueBuilder() {

}

TestExecutorActionQueueBuilder::~TestExecutorActionQueueBuilder() {

}

TEST_F(TestExecutorActionQueueBuilder, smoke) {
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<arl::dm::IModelFieldActionUP>   actions;

    for (uint32_t i=0; i<16; i++) {
        arl::dm::IModelFieldAction *action = m_ctxt->mkModelFieldActionRoot("a", 0);
        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_ctxt->mkModelActivityTraverse(
            action,
            0,
            false,
            0,
            false);
        activities->addActivity(t, true);
    }

    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());
    std::vector<ExecutorActionQueue> queues;
    TaskBuildExecutorActionQueues(m_ctxt->getDebugMgr(), {}, -1).build(
        queues,
        activity_it
    );

    ASSERT_EQ(queues.size(), 1);
    ASSERT_EQ(queues[0].size(), 16);
}

TEST_F(TestExecutorActionQueueBuilder, seq_alt_executors) {
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<IModelFieldActionUP>   actions;

    m_ctxt->getDebugMgr()->enable(true);

    vsc::dm::IDataTypeStruct *claim_t = m_ctxt->mkDataTypeStruct("claim_t");
    m_ctxt->addDataTypeStruct(claim_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec1", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec2", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec3", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec4", claim_t, false));
    m_ctxt->addDataTypeComponent(comp_t);


    // Use a data type in order to get a claim
    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("action_t");
    action_t->addField(m_ctxt->mkTypeFieldExecutorClaim("claim", claim_t, false));
    action_t->setComponentType(comp_t);
    m_ctxt->addDataTypeAction(action_t);

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponent *comp = comp_t->mkRootFieldT<IModelFieldComponent>(
        &build_ctxt,
        "pss_top",
        false);
    IModelFieldExecutor *exec1 = comp->getFieldT<IModelFieldExecutor>(0);
    IModelFieldExecutor *exec2 = comp->getFieldT<IModelFieldExecutor>(1);
    IModelFieldExecutor *exec3 = comp->getFieldT<IModelFieldExecutor>(2);
    IModelFieldExecutor *exec4 = comp->getFieldT<IModelFieldExecutor>(3);

    for (uint32_t i=0; i<16; i++) {
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, "a", false);
        IModelFieldExecutorClaim *claim = action->getFieldT<IModelFieldExecutorClaim>(1);
        claim->setRef((i%2)?exec2:exec1);
        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_ctxt->mkModelActivityTraverse(
            action,
            0, // with_c
            false, // own_with_c
            0, // activity
            false // own_activiy
            );
        activities->addActivity(t, true);
    }

    std::vector<IModelFieldExecutor *> executors({exec1, exec2, exec3, exec4});

    std::vector<ExecutorActionQueue> queues;
    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());
    TaskBuildExecutorActionQueues(m_ctxt->getDebugMgr(), executors, 0).build(
        queues,
        activity_it
    );

    ASSERT_EQ(queues.size(), 4);
    // Expect the primary executor to have
    // - 1 entry publishing its readiness
    // - 15 entries executing actions and waiting for its peer
    // - 3 entries synchronizing with core termination
    ASSERT_EQ(queues[0].size(), 19);
    // Expect the non-primary peer core to have
    // - 1 entry waiting for the primary core 
    // - 16 entries synchronizing
    // - 1 entry notifying the primary core 
    ASSERT_EQ(queues[1].size(), 18); 
    // Expect these idle cores to have
    // - 1 entry waiting for the primary core
    // - 1 entry notifying the primary core
    ASSERT_EQ(queues[2].size(), 2);
    ASSERT_EQ(queues[3].size(), 2);
}

TEST_F(TestExecutorActionQueueBuilder, seq_executors) {
    std::vector<IModelFieldActionUP>   actions;
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));

    m_ctxt->getDebugMgr()->enable(true);

    IDataTypeStruct *claim_t = m_ctxt->mkDataTypeStruct("claim_t");
    m_ctxt->addDataTypeStruct(claim_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec1", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec2", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec3", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec4", claim_t, false));
    m_ctxt->addDataTypeComponent(comp_t);


    // Use a data type in order to get a claim
    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("action_t");
    action_t->addField(m_ctxt->mkTypeFieldExecutorClaim("claim", claim_t, false));
    action_t->setComponentType(comp_t);
    m_ctxt->addDataTypeAction(action_t);

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponent *comp = comp_t->mkRootFieldT<IModelFieldComponent>(
        &build_ctxt,
        "pss_top",
        false);
    IModelFieldExecutor *exec1 = comp->getFieldT<IModelFieldExecutor>(1);
    IModelFieldExecutor *exec2 = comp->getFieldT<IModelFieldExecutor>(2);
    IModelFieldExecutor *exec3 = comp->getFieldT<IModelFieldExecutor>(3);
    IModelFieldExecutor *exec4 = comp->getFieldT<IModelFieldExecutor>(4);
    ASSERT_TRUE(exec1);
    ASSERT_TRUE(exec2);
    ASSERT_TRUE(exec3);
    ASSERT_TRUE(exec4);

    for (uint32_t i=0; i<16; i++) {
        char name[64];
        sprintf(name, "a%d", i);
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, name, false);
        IModelFieldExecutorClaim *claim = action->getFieldT<IModelFieldExecutorClaim>(1);
        claim->setRef((i<8)?exec1:exec2);
        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_ctxt->mkModelActivityTraverse(
            action,
            0, // with_c
            false,
            0,
            false);
        activities->addActivity(t, true);
    }

    std::vector<IModelFieldExecutor *> executors({exec1, exec2, exec3, exec4});

    std::vector<ExecutorActionQueue> queues;
    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());
    TaskBuildExecutorActionQueues(m_ctxt->getDebugMgr(), executors, 0).build(
        queues,
        activity_it
    );

    ASSERT_EQ(queues.size(), 4);
    // The primary executor has
    // - 1 initial notification
    // - 8 synchronizations and executions
    // - 3 final depends
    for (uint32_t i=0; i<queues[0].size(); i++) {
        switch (queues[0].at(i).kind) {
            case ExecutorActionQueueEntryKind::Action: {
                fprintf(stdout, "[%d] Action: action %s\n", i, queues[0].at(i).action->name().c_str());
            } break;
            case ExecutorActionQueueEntryKind::Depend: {
                fprintf(stdout, "[%d] Depend: %d %d \n", 
                    i, 
                    queues[0].at(i).executor_id,
                    queues[0].at(i).action_id);
            } break;
            case ExecutorActionQueueEntryKind::Notify: {
                fprintf(stdout, "[%d] Notify: %d\n", i, queues[0].at(i).action_id);
            } break;

            default:
                fprintf(stdout, "Entry %d: %d\n", i, queues[0].at(i).kind);
                break;
        }
    }
    ASSERT_EQ(queues[0].size(), 12);
    // The non-primary executor has
    // - 1 initial depend
    // - 9 synchronizations and executions
    // - 1 final notification
    ASSERT_EQ(queues[1].size(), 11); 
    ASSERT_EQ(queues[2].size(), 2);
    ASSERT_EQ(queues[3].size(), 2);
}

TEST_F(TestExecutorActionQueueBuilder, seq_par_diff_executor) {
    IModelActivityScopeUP activities(m_ctxt->mkModelActivityScope(ModelActivityScopeT::Sequence));
    std::vector<IModelFieldActionUP>   actions;

    m_ctxt->getDebugMgr()->enable(true);

    IDataTypeStruct *claim_t = m_ctxt->mkDataTypeStruct("claim_t");
    m_ctxt->addDataTypeStruct(claim_t);

    IDataTypeComponent *comp_t = m_ctxt->mkDataTypeComponent("comp_t");
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec1", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec2", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec3", claim_t, false));
    comp_t->addField(m_ctxt->mkTypeFieldExecutor("exec4", claim_t, false));
    m_ctxt->addDataTypeComponent(comp_t);


    // Use a data type in order to get a claim
    IDataTypeAction *action_t = m_ctxt->mkDataTypeAction("action_t");
    action_t->addField(m_ctxt->mkTypeFieldExecutorClaim("claim", claim_t, false));
    action_t->setComponentType(comp_t);
    m_ctxt->addDataTypeAction(action_t);

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    IModelFieldComponent *comp = comp_t->mkRootFieldT<IModelFieldComponent>(
        &build_ctxt,
        "pss_top",
        false);
    IModelFieldExecutor *exec1 = comp->getFieldT<IModelFieldExecutor>(0);
    IModelFieldExecutor *exec2 = comp->getFieldT<IModelFieldExecutor>(1);
    IModelFieldExecutor *exec3 = comp->getFieldT<IModelFieldExecutor>(2);
    IModelFieldExecutor *exec4 = comp->getFieldT<IModelFieldExecutor>(3);

    for (uint32_t i=0; i<16; i++) {
        IModelFieldAction *action = action_t->mkRootFieldT<IModelFieldAction>(
            &build_ctxt, "a", false);
        IModelFieldExecutorClaim *claim = action->getFieldT<IModelFieldExecutorClaim>(1);
        claim->setRef((i<8)?exec1:exec2);
        actions.push_back(IModelFieldActionUP(action));
        IModelActivityTraverse *t = m_ctxt->mkModelActivityTraverse(
            action,
            0,
            false,
            0,
            false);
        activities->addActivity(t, true);
    }

    std::vector<IModelFieldExecutor *> executors({exec1, exec2, exec3, exec4});

    std::vector<ExecutorActionQueue> queues;
    IModelEvalIterator *activity_it = m_ctxt->mkModelEvalIterator(activities.get());
    TaskBuildExecutorActionQueues(m_ctxt->getDebugMgr(), executors, 0).build(
        queues,
        activity_it
    );

    ASSERT_EQ(queues.size(), 4);
    ASSERT_EQ(queues[0].size(), 8);
    ASSERT_EQ(queues[1].size(), 9); 
    ASSERT_EQ(queues[2].size(), 0);
    ASSERT_EQ(queues[3].size(), 0);
}

}
}
}
