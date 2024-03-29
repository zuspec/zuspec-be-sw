/*
 * GeneratorMultiCoreEmbCTest.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "GeneratorMultiCoreEmbCTest.h"
#include "ModelEvalIteratorTypeCollectorListener.h"
#include "TaskBuildExecutorActionQueues.h"
#include "TaskCollectSortTypes.h"
#include "TaskGenerateEmbCActionExec.h"
#include "TaskGenerateEmbCCompTreeData.h"
#include "TaskGenerateEmbCStruct.h"
#include "TaskMangleTypeNames.h"
#include "TaskGenerateActionQueueCalls.h"
#include "TaskGenerateFuncProtoEmbeddedC.h"


namespace zsp {
namespace be {
namespace sw {


GeneratorMultiCoreEmbCTest::GeneratorMultiCoreEmbCTest(
        dmgr::IDebugMgr                                   *dmgr,
        const std::vector<arl::dm::IModelFieldExecutor *> &executors,
        int32_t                                           dflt_exec,
        IOutput                                           *out_h,
        IOutput                                           *out_c) :
            m_dmgr(dmgr), m_executors(executors.begin(), executors.end()),
            m_dflt_exec(dflt_exec), m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("GeneratorMultiCoreEmbCTest", dmgr);
    m_entry_name = "entry";
}

GeneratorMultiCoreEmbCTest::~GeneratorMultiCoreEmbCTest() {

}

void GeneratorMultiCoreEmbCTest::generate(
    arl::dm::IModelFieldComponentRoot       *root,
    arl::dm::IModelEvalIterator             *it) {
    std::vector<arl::dm::IModelFieldExecutor *> execs;

    // Create action queues for each
    std::vector<ExecutorActionQueue> queues;
    for (auto it=m_executors.begin(); it!=m_executors.end(); it++) {
        execs.push_back(*it);
    }

    TaskMangleTypeNames mangler(m_dmgr, &m_name_m);
    TaskCollectSortTypes type_s(m_dmgr, [&](vsc::dm::IDataTypeStruct *t) { });

    // First, collect all types from the component tree
    for (std::vector<arl::dm::IDataTypeComponent *>::const_iterator
        it=root->getCompTypes().begin();
        it!=root->getCompTypes().end(); it++) {
        type_s.collect(*it);
    }

    // Listen to the iterator to identify types and 
    // properly mangle them. This results in a unified name map and
    // list of all types.
    ModelEvalIteratorTypeCollectorListener type_collector_l(&type_s);
    it->addListener(&type_collector_l);

    // Organize actions into queues and collect types from actions
    TaskBuildExecutorActionQueues(m_dmgr, execs, m_dflt_exec).build(queues, it);


    // Generate Types (.h)
    std::vector<vsc::dm::IDataTypeStruct *>     types;
    std::vector<arl::dm::IDataTypeFunction *>   funcs;
    type_s.sort(types, funcs);

    for (std::vector<vsc::dm::IDataTypeStruct *>::const_iterator
        it=types.begin();
        it!=types.end(); it++) {
        // TODO:
        TaskGenerateEmbCStruct(0, m_out_h).generate(*it);
    }

    // Generate prototypes for import functions to the .h file
    // and prototypes for local function to the .c file
    for (std::vector<arl::dm::IDataTypeFunction *>::const_iterator
        it=funcs.begin();
        it!=funcs.end(); it++) {
        if ((*it)->getImportSpecs().size()) {
            // TODO:
            TaskGenerateFuncProtoEmbeddedC(0).generate(m_out_h, *it);
        } else {
            TaskGenerateFuncProtoEmbeddedC(0).generate(m_out_c, *it);
        }
    }

    // Generate the component tree (.c)
    TaskGenerateEmbCCompTreeData(m_dmgr, m_out_c, &m_name_m).generate(root);

    // TODO: Generate the resource array
    // Need to share this with

    // TODO: How to manage flow objects?
    // - Must be able to share objects between actions that read/write them
    // - Must be able to recycle objects
    // Each software image gets a copy based on its use

    // Foreach output source file
    // - Collect functions called from the action types that will be placed in that file
    // - Generate

    // TODO: Generate Exec-body functions for actions
    // - Must collect action types on a per-file basis
    // - Must collect dependent functions on a per-file basis
    // - Must prototype 
    for (std::vector<vsc::dm::IDataTypeStruct *>::const_iterator
        it=types.begin();
        it!=types.end(); it++) {
        if (dynamic_cast<arl::dm::IDataTypeAction *>(*it)) {
            TaskGenerateEmbCActionExec(
                m_dmgr, 
                &m_name_m,
                m_out_c).generate(dynamic_cast<arl::dm::IDataTypeAction *>(*it));
        }
    }

    // TODO: Generate a 'core-main' for each executor
    TaskGenerateActionQueueCalls gen_queue_calls(m_dmgr, &m_name_m, root);
    for (uint32_t i=0; i<queues.size(); i++) {
        m_out_c->println("void core_%d_%s() {", i, m_entry_name.c_str());
        m_out_c->inc_ind();

        gen_queue_calls.generate(m_out_c, queues.at(i));

        m_out_c->dec_ind();
        m_out_c->println("}");
    }
    m_out_c->println("");

    // TODO: Generate a 'main' for the entire test
    // - Accepts a core-id and invokes appropriate per-core dispatch function

    m_out_c->println("void %s(int unsigned coreid) {", m_entry_name.c_str());
    m_out_c->inc_ind();
    m_out_c->println("switch (coreid) {");
    m_out_c->inc_ind();
    for (uint32_t i=0; i<queues.size(); i++) {
        m_out_c->println("case %d: core_%d_%s(); break;",
            i, i, m_entry_name.c_str());
    }
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->dec_ind();
    m_out_c->println("}");

}

dmgr::IDebug *GeneratorMultiCoreEmbCTest::m_dbg = 0;

}
}
}
