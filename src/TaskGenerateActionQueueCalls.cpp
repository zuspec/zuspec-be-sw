/*
 * TaskGenerateActionQueueCalls.cpp
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
#include "TaskGenerateActionQueueCalls.h"
#include "TaskGenerateEmbCDataType.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateActionQueueCalls::TaskGenerateActionQueueCalls(
    dmgr::IDebugMgr                     *dmgr,
    NameMap                             *name_m) : 
        m_dmgr(dmgr), m_name_m(name_m) {

}

TaskGenerateActionQueueCalls::~TaskGenerateActionQueueCalls() {

}

void TaskGenerateActionQueueCalls::generate(
        IOutput                                     *out,
        const std::vector<ExecutorActionQueueEntry> &ops) {

    for (std::vector<ExecutorActionQueueEntry>::const_iterator
        it=ops.begin();
        it!=ops.end(); it++) {
        switch (it->kind) {
            case ExecutorActionQueueEntryKind::Action: {
                out->println("{");
                out->inc_ind();
                out->indent();
                TaskGenerateEmbCDataType(out, m_name_m).generate(
                    it->action->getDataTypeT<vsc::dm::IDataTypeStruct>());
                out->write(" ctx;\n");
                out->println("action_%s_exec(&ctx);", m_name_m->getName(
                    it->action->getDataTypeT<vsc::dm::IDataTypeStruct>()).c_str());
                out->dec_ind();
                out->println("}");
            } break;

            case ExecutorActionQueueEntryKind::Depend: {

            } break;
        }

    }
}

dmgr::IDebug *TaskGenerateActionQueueCalls::m_dbg = 0;

}
}
}
