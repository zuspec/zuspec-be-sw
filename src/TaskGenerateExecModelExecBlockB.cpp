/*
 * TaskGenerateExecModelExecBlockB.cpp
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
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelExecBlockB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelExecBlockB::TaskGenerateExecModelExecBlockB(
    TaskGenerateExecModel           *gen,
    IGenRefExpr                     *refgen,
    IOutput                         *out) :
    m_gen(gen), m_refgen(refgen), m_out(out) {

}

TaskGenerateExecModelExecBlockB::~TaskGenerateExecModelExecBlockB() {

}

void TaskGenerateExecModelExecBlockB::generate(
        const std::string                           &fname,
        const std::string                           &tname,
        const std::vector<arl::dm::ITypeExecUP>     &execs) {

    m_gen->getOutC()->println("static void %s_init(struct %s_s *actor, %s *this_p) {",
        fname.c_str(),
        m_gen->getActorName().c_str(),
        tname.c_str());
    m_gen->getOutC()->inc_ind();
    m_gen->getOutC()->println("this_p->task.func = (zsp_rt_task_f)&%s_run;",
        fname.c_str());
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");

    m_gen->getOutC()->println("static zsp_rt_task_t *%s_run(struct %s_s *actor, %s *this_p) {",
        fname.c_str(),
        m_gen->getActorName().c_str(),
        tname.c_str());
    m_gen->getOutC()->inc_ind();
    m_gen->getOutC()->println("return 0;");

    // TODO:

    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");
}

}
}
}
