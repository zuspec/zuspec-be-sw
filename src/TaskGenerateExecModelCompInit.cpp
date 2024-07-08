/*
 * TaskGenerateExecModelCompInit.cpp
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
#include "TaskGenerateExecModelCompInit.h"
#include "TaskGenerateExecModelExecBlockNB.h"
#include "GenRefExprExecModel.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelCompInit::TaskGenerateExecModelCompInit(
    TaskGenerateExecModel *gen) : TaskGenerateExecModelStructInit(gen) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelCompInit", gen->getDebugMgr());

    m_mode = Mode::DataFieldInit;
}

TaskGenerateExecModelCompInit::~TaskGenerateExecModelCompInit() {

}

void TaskGenerateExecModelCompInit::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent");
    if (m_depth == 0) {
        /*
        GenRefExprExecModel refgen(
            m_gen, 
            t,
            "this_p",
            true);
        const std::vector<arl::dm::ITypeExecUP> &init_down = 
            t->getExecs(arl::dm::ExecKindT::InitDown);
        const std::vector<arl::dm::ITypeExecUP> &init_up = 
            t->getExecs(arl::dm::ExecKindT::InitUp);

        // First, generate exec init_* functions if we'll be calling them
        if (init_down.size()) {
            // Invoke the init_down exec block
            TaskGenerateExecModelExecBlockNB(m_gen, &refgen, m_out_c).generate(
                m_gen->getNameMap()->getName(t) + "__init_down",
                "struct " + m_gen->getNameMap()->getName(t) + "_s",
                init_down
            );
        }

        if (init_up.size()) {
            // Invoke the init_up exec block
            TaskGenerateExecModelExecBlockNB(m_gen, &refgen, m_out_c).generate(
                m_gen->getNameMap()->getName(t) + "__init_up",
                "struct " + m_gen->getNameMap()->getName(t) + "_s",
                init_down
            );
        }
         */

        m_out_c->println("void %s__init(struct %s_s *actor, struct %s_s *this_p) {",
            m_gen->getNameMap()->getName(t).c_str(),
            m_gen->getActorName().c_str(),
            m_gen->getNameMap()->getName(t).c_str());
        m_out_c->inc_ind();
        m_depth++;
        m_subcomp_init.clear();
        m_subcomp_init.inc_ind();
        for (std::vector<vsc::dm::ITypeFieldUP>::const_iterator
            it=t->getFields().begin();
            it!=t->getFields().end(); it++) {
            (*it)->accept(m_this);
        }
        m_subcomp_init.dec_ind();
        m_depth--;

        /*
        if (init_down.size()) {
            m_out_c->println("%s__init_down(actor, this_p);", 
                m_gen->getNameMap()->getName(t).c_str());
        }

        m_out_c->writes(m_subcomp_init.getValue());

        
        if (init_up.size()) {
            m_out_c->println("%s__init_up(actor, this_p);", 
                m_gen->getNameMap()->getName(t).c_str());
        }
         */

        m_out_c->dec_ind();
        m_out_c->println("}");
    } else {
        // Call init for the compound field
        m_subcomp_init.println("%s__init(actor, (struct %s_s *)&this_p->%s);",
            m_gen->getNameMap()->getName(t).c_str(),
            m_gen->getNameMap()->getName(t).c_str(),
            m_field->name().c_str());
    }

    DEBUG_LEAVE("visitDataTypeComponent");
}

}
}
}
