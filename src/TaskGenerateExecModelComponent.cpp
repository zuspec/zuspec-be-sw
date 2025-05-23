/*
 * TaskGenerateExecModelComponent.cpp
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
#include "TaskGenerateExecModelComponent.h"
#include "TaskGenerateExecModelCompStruct.h"
#include "TaskGenerateExecModelCompExecInit.h"
#include "TaskGenerateExecModelCompInit.h"
#include "TaskGenerateExecModelCompStruct.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelComponent::TaskGenerateExecModelComponent(
    TaskGenerateExecModel *gen) : m_gen(gen) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelComponent", gen->getDebugMgr());
}

TaskGenerateExecModelComponent::~TaskGenerateExecModelComponent() {

}

void TaskGenerateExecModelComponent::generate(arl::dm::IDataTypeComponent *comp_t) {
    DEBUG_ENTER("generate");

    // Generate the component struct
//    TaskGenerateExecModelCompStruct(m_gen, m_gen->getOutHPrv()).generate(comp_t);

    TaskGenerateExecModelCompInit(m_gen).generate(comp_t);

    TaskGenerateExecModelCompExecInit(m_gen, m_gen->getOutC()).generate(comp_t);

/*
    // First, handle forward declaration
    m_mode = Mode::FwdDecl;
    comp_t->accept(m_this);

    m_mode = Mode::Decl;
    comp_t->accept(m_this);
 */

    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelComponent::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent");

    switch (m_mode) {
        case Mode::FwdDecl: {
            if (!m_gen->fwdDecl(t)) {
                // Go ahead and forward-declare 
                /*
                TaskGenerateFwdDecl(
                    m_gen->getDebugMgr(),
                    m_gen->getNameMap(),
                    m_gen->getOutHPrv()).generate(t);
                 */
                m_gen->getOutHPrv()->println("static void %s_init(struct %s_s *actor, struct %s_s *obj);",
                    m_gen->getNameMap()->getName(t).c_str(),
                    m_gen->getActorName().c_str(),
                    m_gen->getNameMap()->getName(t).c_str());
            }

            // Recurse to find other 
            for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
                it=t->getFields().begin();
                it!=t->getFields().end(); it++) {
                (*it)->accept(m_this);
            }
        } break;

        case Mode::Decl: {
            std::unordered_set<vsc::dm::IDataType *>::const_iterator it;

            if ((it=m_decl_s.find(t)) == m_decl_s.end()) {
                m_decl_s.insert(t);

                // Recurse first, such that we get dependencies covered before they're used
                for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
                    it=t->getFields().begin();
                    it!=t->getFields().end(); it++) {
                    (*it)->accept(m_this);
                }

//                TaskGenerateExecModelCompStruct(m_gen).generate(t);

                TaskGenerateExecModelCompInit(m_gen).generate(t);


            }
        } break;
    }

    DEBUG_LEAVE("visitDataTypeComponent");
}

dmgr::IDebug *TaskGenerateExecModelComponent::m_dbg = 0;

}
}
}
