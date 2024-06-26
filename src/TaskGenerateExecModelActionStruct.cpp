/*
 * TaskGenerateExecModelActionStruct.cpp
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
#include "dmgr/impl/DebugMacros.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelActionStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelActionStruct::TaskGenerateExecModelActionStruct(
    TaskGenerateExecModel       *gen,
    IOutput                     *out) : TaskGenerateExecModelStruct(gen, out) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelActionStruct", gen->getDebugMgr());

}

TaskGenerateExecModelActionStruct::~TaskGenerateExecModelActionStruct() {

}

void TaskGenerateExecModelActionStruct::generate(arl::dm::IDataTypeAction *action_t) {
    DEBUG_ENTER("generate");

    m_depth = 0;
    m_ptr = 0;
    m_field = 0;
    m_field_m.clear();

    m_out->println("typedef struct %s_s {", 
        m_gen->getNameMap()->getName(action_t).c_str());
    m_out->inc_ind();
    m_out->println("zsp_rt_task_t task;");

    // Setup to handle shadowed variables
    for (std::vector<vsc::dm::ITypeFieldUP>::const_reverse_iterator
        it=action_t->getFields().rbegin();
        it!=action_t->getFields().rend(); it++) {
        FieldM::iterator fit;
          
        if ((fit=m_field_m.find((*it)->name())) != m_field_m.end()) {
            fit->second++;
        } else {
            m_field_m.insert({(*it)->name(), 0});
        }
    }

    for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
        it=action_t->getFields().begin();
        it!=action_t->getFields().end(); it++) {
        (*it)->accept(m_this);
    }

    // Need to add elements for activity or exec blocks

    m_out->dec_ind();
    m_out->println("} %s_t;", 
        m_gen->getNameMap()->getName(action_t).c_str());

    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelActionStruct::visitTypeFieldRef(vsc::dm::ITypeFieldRef *f) {
    DEBUG_ENTER("visitTypeFieldRef");
    if (f->name() != "comp") {
        TaskGenerateExecModelStruct::visitTypeField(f);
    }
    DEBUG_LEAVE("visitTypeFieldRef");
}

}
}
}
