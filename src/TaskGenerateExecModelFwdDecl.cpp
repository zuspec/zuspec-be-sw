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
    item->accept(m_this);
}

void TaskGenerateExecModelFwdDecl::visitDataTypeAction(arl::dm::IDataTypeAction *t) {
    DEBUG_ENTER("visitDataTypeAction %s", t->name().c_str());
    m_out->println("struct %s_s;", m_gen->getNameMap()->getName(t).c_str());
    m_out->println("static void %s__init(struct %s_s *actor, struct %s_s *this_p);",
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());
    m_out->println("static void %s__run(struct %s_s *actor, struct %s_s *this_p);",
        m_gen->getNameMap()->getName(t).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(t).c_str());


    DEBUG_LEAVE("visitDataTypeAction %s", t->name().c_str());
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
