/*
 * TaskGenerateExecModelFwdDecl.cpp
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
#include "zsp/be/sw/INameMap.h"
#include "ITaskGenerateExecModelCustomGen.h"
#include "TaskCheckIsExecBlocking.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelFwdDecl.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelFwdDecl::TaskGenerateExecModelFwdDecl(
    TaskGenerateExecModel   *gen,
    IOutput                 *out) : m_gen(gen), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelFwdDecl", gen->getDebugMgr());
}

TaskGenerateExecModelFwdDecl::~TaskGenerateExecModelFwdDecl() {

}

void TaskGenerateExecModelFwdDecl::generate(vsc::dm::IAccept *item) {
    ITaskGenerateExecModelCustomGen *custom_gen = 0;
    if (dynamic_cast<vsc::dm::IDataType *>(item)) {
        custom_gen = dynamic_cast<ITaskGenerateExecModelCustomGen *>(
            dynamic_cast<vsc::dm::IDataType *>(item)->getAssociatedData());
    }

    if (custom_gen) {
        custom_gen->genFwdDecl(
            m_gen,
            m_out,
            dynamic_cast<vsc::dm::IDataType *>(item)
        );
    } else {
        generate_dflt(item);
    }
}

void TaskGenerateExecModelFwdDecl::generate_dflt(vsc::dm::IAccept *item) {
    item->accept(m_this);
}

void TaskGenerateExecModelFwdDecl::visitDataTypeAction(arl::dm::IDataTypeAction *t) {
    DEBUG_ENTER("visitDataTypeAction %s", t->name().c_str());
    m_out->println("struct %s_s;", m_gen->getNameMap()->getName(t).c_str());
    m_out->println("static void %s__init(struct %s_s *actor, struct %s_s *this_p);",
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());
    m_out->println("static zsp_rt_task_t *%s__run(struct %s_s *actor, struct %s_s *this_p);",
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());
    if (t->getExecs(arl::dm::ExecKindT::Body).size()) {
        if (TaskCheckIsExecBlocking(m_gen->getDebugMgr(), false).check(
            t->getExecs(arl::dm::ExecKindT::Body))) {
            m_out->println("struct %s__body_s;",
                m_gen->getNameMap()->getName(t).c_str());
            m_out->println("static void %s__body_init(struct %s_s *actor, struct %s__body_s *this_p);",
                m_gen->getNameMap()->getName(t).c_str(),
                m_gen->getActorName().c_str(),
                m_gen->getNameMap()->getName(t).c_str());
            m_out->println("static zsp_rt_task_t *%s__body_run(struct %s_s *actor, struct %s__body_s *this_p);",
                m_gen->getNameMap()->getName(t).c_str(),
                m_gen->getActorName().c_str(),
                m_gen->getNameMap()->getName(t).c_str());
        } else {
            m_out->println("static void %s__body(struct %s_s *actor, struct %s_s *this_p);",
                m_gen->getNameMap()->getName(t).c_str(),
                m_gen->getActorName().c_str(),
                m_gen->getNameMap()->getName(t).c_str());
        }
    }
    if (t->activities().size()) {
        m_out->println("struct %s__activity_s;",
            m_gen->getNameMap()->getName(t).c_str());
        m_out->println("static zsp_rt_task_t *%s__activity_run(struct %s_s *actor, struct %s__activity_s *this_p);",
            m_gen->getNameMap()->getName(t).c_str(),
            m_gen->getActorName().c_str(),
            m_gen->getNameMap()->getName(t).c_str());
        for (std::vector<arl::dm::ITypeFieldActivityUP>::const_iterator
            it=t->activities().begin();
            it!=t->activities().end(); it++) {
            (*it)->getDataType()->accept(m_this);
        }
    }
    if (t->getExecs(arl::dm::ExecKindT::PreSolve).size()) {
        m_out->println("static void %s__pre_solve(struct %s_s *actor, struct %s_s *this_p);",
            m_gen->getNameMap()->getName(t).c_str(),
            m_gen->getActorName().c_str(),
            m_gen->getNameMap()->getName(t).c_str());
    }
    if (t->getExecs(arl::dm::ExecKindT::PostSolve).size()) {
        m_out->println("static void %s__post_solve(struct %s_s *actor, struct %s_s *this_p);",
            m_gen->getNameMap()->getName(t).c_str(),
            m_gen->getActorName().c_str(),
            m_gen->getNameMap()->getName(t).c_str());
    }


    DEBUG_LEAVE("visitDataTypeAction %s", t->name().c_str());
}

void TaskGenerateExecModelFwdDecl::visitDataTypeActivitySequence(arl::dm::IDataTypeActivitySequence *t) {
    DEBUG_ENTER("visitDataTypeActivitySequence");
    m_out->println("struct activity_%p_s;", t);
    m_out->println("static void activity_%p_init(struct %s_s *actor, struct activity_%p_s *this_p);", 
        t,
        m_gen->getActorName().c_str(),
        t);
    m_out->println("static zsp_rt_task_t *activity_%p_run(struct %s_s *actor, struct activity_%p_s *this_p);", 
        t,
        m_gen->getActorName().c_str(),
        t);
    for (std::vector<arl::dm::ITypeFieldActivityUP>::const_iterator
        it=t->getActivities().begin();
        it!=t->getActivities().end(); it++) {
        (*it)->getDataType()->accept(m_this);
    }
    DEBUG_LEAVE("visitDataTypeActivitySequence");
}

void TaskGenerateExecModelFwdDecl::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    DEBUG_ENTER("visitDataTypeComponent %s", t->name().c_str());
    m_out->println("struct %s_s;", m_gen->getNameMap()->getName(t).c_str());
    m_out->println("static void %s__init(struct %s_s *actor, struct %s_s *this_p);",
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());

    // TODO: need to find associated functions

    DEBUG_LEAVE("visitDataTypeComponent");
}

void TaskGenerateExecModelFwdDecl::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());
    m_out->println("struct %s_s;", m_gen->getNameMap()->getName(t).c_str());
    m_out->println("static void %s__init(struct %s_s *actor, struct %s_s *this_p);",
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());

    // TODO: need to find associated functions

    DEBUG_LEAVE("visitDataTypeStruct");
}

dmgr::IDebug *TaskGenerateExecModelFwdDecl::m_dbg = 0;

}
}
}
