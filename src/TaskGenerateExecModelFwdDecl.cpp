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
#include "zsp/arl/dm/impl/TaskActionHasMemClaim.h"
#include "zsp/be/sw/INameMap.h"
#include "ITaskGenerateExecModelCustomGen.h"
#include "TaskCheckIsExecBlocking.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelFwdDecl.h"
#include "TaskHasDtorFields.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelFwdDecl::TaskGenerateExecModelFwdDecl(
    IContext                *ctxt,
    IOutput                 *out) : m_ctxt(ctxt), m_out(out) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelFwdDecl", ctxt->getDebugMgr());
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
            m_ctxt,
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
    m_out->println("struct %s_s;", m_ctxt->nameMap()->getName(t).c_str());
    m_out->println("static void %s__init(struct %s_s *actor, struct %s_s *this_p);",
        m_ctxt->nameMap()->getName(t).c_str(),
        "actor"/*m_gen->getActorName().c_str()*/,
        m_ctxt->nameMap()->getName(t).c_str());
    m_out->println("static zsp_rt_task_t *%s__run(struct %s_s *actor, struct %s_s *this_p);",
        m_ctxt->nameMap()->getName(t).c_str(),
        "actor"/*m_gen->getActorName().c_str()*/,
        m_ctxt->nameMap()->getName(t).c_str());
    m_out->println("static void %s__dtor(struct %s_s *actor, struct %s_s *this_p);",
        m_ctxt->nameMap()->getName(t).c_str(),
        "actor"/*m_gen->getActorName().c_str()*/,
        m_ctxt->nameMap()->getName(t).c_str());
    if (t->getExecs(arl::dm::ExecKindT::Body).size()) {
        if (TaskCheckIsExecBlocking(m_ctxt->getDebugMgr(), false).check(
            t->getExecs(arl::dm::ExecKindT::Body))) {
            m_out->println("struct %s__body_s;",
                m_ctxt->nameMap()->getName(t).c_str());
            m_out->println("static void %s__body_init(struct %s_s *actor, struct %s__body_s *this_p);",
                m_ctxt->nameMap()->getName(t).c_str(),
                "actor"/*m_gen->getActorName().c_str()*/,
                m_ctxt->nameMap()->getName(t).c_str());
            m_out->println("static zsp_rt_task_t *%s__body_run(struct %s_s *actor, zsp_rt_task_t *this_p);",
                m_ctxt->nameMap()->getName(t).c_str(),
                "actor"/*m_gen->getActorName().c_str()*/);
            for (std::vector<arl::dm::ITypeExecUP>::const_iterator
                it=t->getExecs(arl::dm::ExecKindT::Body).begin();
                it!=t->getExecs(arl::dm::ExecKindT::Body).end(); it++) {
                (*it)->accept(m_this);
            }
        } else {
            m_out->println("static void %s__body(struct %s_s *actor, struct %s_s *this_p);",
                m_ctxt->nameMap()->getName(t).c_str(),
                "actor"/*m_gen->getActorName().c_str()*/,
                m_ctxt->nameMap()->getName(t).c_str());
        }
    }
    if (t->activities().size()) {
        m_out->println("struct %s__activity_s;",
            m_ctxt->nameMap()->getName(t).c_str());
        m_out->println("static zsp_rt_task_t *%s__activity_run(struct %s_s *actor, struct %s__activity_s *this_p);",
            m_ctxt->nameMap()->getName(t).c_str(),
            "actor"/*m_gen->getActorName().c_str()*/,
            m_ctxt->nameMap()->getName(t).c_str());
        for (std::vector<arl::dm::ITypeFieldActivityUP>::const_iterator
            it=t->activities().begin();
            it!=t->activities().end(); it++) {
            (*it)->getDataType()->accept(m_this);
        }
    }
    if (t->getExecs(arl::dm::ExecKindT::PreSolve).size()) {
        m_out->println("static void %s__pre_solve(struct %s_s *actor, struct %s_s *this_p);",
            m_ctxt->nameMap()->getName(t).c_str(),
            "actor"/*m_gen->getActorName().c_str()*/,
            m_ctxt->nameMap()->getName(t).c_str());
    }
    if (t->getExecs(arl::dm::ExecKindT::PostSolve).size()) {
        m_out->println("static void %s__post_solve(struct %s_s *actor, struct %s_s *this_p);",
            m_ctxt->nameMap()->getName(t).c_str(),
            "actor"/*m_gen->getActorName().c_str()*/,
            m_ctxt->nameMap()->getName(t).c_str());
    }
    if (arl::dm::TaskActionHasMemClaim().check(t)) {
        m_out->println("static void %s__alloc(struct %s_s *actor, struct %s_s *this_p);",
            m_ctxt->nameMap()->getName(t).c_str(),
            "actor"/*m_gen->getActorName().c_str()*/,
            m_ctxt->nameMap()->getName(t).c_str());
    }
    if (t->getExecs(arl::dm::ExecKindT::PreBody).size()) {
        m_out->println("static void %s__pre_body(struct %s_s *actor, struct %s_s *this_p);",
            m_ctxt->nameMap()->getName(t).c_str(),
            "actor"/*m_gen->getActorName().c_str()*/,
            m_ctxt->nameMap()->getName(t).c_str());
    }

    DEBUG_LEAVE("visitDataTypeAction %s", t->name().c_str());
}

void TaskGenerateExecModelFwdDecl::visitDataTypeActivitySequence(arl::dm::IDataTypeActivitySequence *t) {
    DEBUG_ENTER("visitDataTypeActivitySequence");
    m_out->println("struct activity_%p_s;", t);
    m_out->println("static void activity_%p__init(struct %s_s *actor, struct activity_%p_s *this_p);", 
        t,
        "actor"/*m_gen->getActorName().c_str()*/,
        t);
    m_out->println("static zsp_rt_task_t *activity_%p__run(struct %s_s *actor, struct activity_%p_s *this_p);", 
        t,
        "actor"/*m_gen->getActorName().c_str()*/,
        t);
    m_out->println("static void activity_%p__dtor(struct %s_s *actor, struct activity_%p_s *this_p);", 
        t,
        "actor"/*m_gen->getActorName().c_str()*/,
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
    m_out->println("struct %s_s;", m_ctxt->nameMap()->getName(t).c_str());
    m_out->println("static void %s__init(struct %s_s *actor, struct %s_s *this_p);",
        m_ctxt->nameMap()->getName(t).c_str(),
        "actor"/*m_gen->getActorName().c_str()*/,
        m_ctxt->nameMap()->getName(t).c_str());

    // TODO: need to find associated functions

    DEBUG_LEAVE("visitDataTypeComponent");
}

void TaskGenerateExecModelFwdDecl::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("visitDataTypeStruct %s", t->name().c_str());
    m_out->println("struct %s_s;", m_ctxt->nameMap()->getName(t).c_str());
    m_out->println("static void %s__init(struct %s_s *actor, struct %s_s *this_p);",
        m_ctxt->nameMap()->getName(t).c_str(),
        "actor"/*m_gen->getActorName().c_str()*/,
        m_ctxt->nameMap()->getName(t).c_str());
    m_out->println("static void %s__dtor(struct %s_s *actor, struct %s_s *this_p);",
        m_ctxt->nameMap()->getName(t).c_str(),
        "actor"/*m_gen->getActorName().c_str()*/,
        m_ctxt->nameMap()->getName(t).c_str());

    // TODO: need to find associated functions

    DEBUG_LEAVE("visitDataTypeStruct");
}

void TaskGenerateExecModelFwdDecl::visitTypeExecProc(arl::dm::ITypeExecProc *t) {
    DEBUG_ENTER("visitTypeExecProc");
    t->getBody()->accept(m_this);

    DEBUG_LEAVE("visitTypeExecProc");
}

void TaskGenerateExecModelFwdDecl::visitTypeProcStmtScope(arl::dm::ITypeProcStmtScope *s) {
    DEBUG_ENTER("visitTypeProcStmtScope");
    if (TaskCheckIsExecBlocking(
        m_ctxt->getDebugMgr(), true/*m_gen->isTargetImpBlocking()*/).check(s)) {
        m_out->println("struct exec_%p_s;", s);
        m_out->println("static void exec_%p__init(struct %s_s *actor, struct exec_%p_s *this_s);",
            s,
            "actor"/*m_gen->getActorName().c_str()*/,
            s);
        m_out->println("static zsp_rt_task_t *exec_%p__run(struct %s_s *actor, struct exec_%p_s *this_s);",
            s,
            "actor"/*m_gen->getActorName().c_str()*/,
            s);
        m_out->println("static void exec_%p__dtor(struct %s_s *actor, struct exec_%p_s *this_s);",
            s,
            "actor"/*m_gen->getActorName().c_str()*/,
            s);
        
        for (std::vector<arl::dm::ITypeProcStmtUP>::const_iterator
            it=s->getStatements().begin();
            it!=s->getStatements().end(); it++) {
            (*it)->accept(m_this);
        }
    }
    DEBUG_LEAVE("visitTypeProcStmtScope");
}

dmgr::IDebug *TaskGenerateExecModelFwdDecl::m_dbg = 0;

}
}
}
