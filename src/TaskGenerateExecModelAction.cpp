/*
 * TaskGenerateExecModelAction.cpp
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
#include "GenRefExprExecModel.h"
#include "TaskCheckIsExecBlocking.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelAction.h"
#include "TaskGenerateExecModelActionAlloc.h"
#include "TaskGenerateExecModelActionInit.h"
#include "TaskGenerateExecModelActionStruct.h"
#include "TaskGenerateExecModelActivity.h"
#include "TaskGenerateExecModelExecBlockB.h"
#include "TaskGenerateExecModelExecBlockNB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModelAction::TaskGenerateExecModelAction(
    TaskGenerateExecModel   *gen,
    bool                    is_root) : m_gen(gen), m_is_root(is_root), m_depth(0) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModelAction", gen->getDebugMgr());
}

TaskGenerateExecModelAction::~TaskGenerateExecModelAction() {

}

void TaskGenerateExecModelAction::generate(arl::dm::IDataTypeAction *action) {
    DEBUG_ENTER("generate");
    GenRefExprExecModel refgen(
        m_gen,
        action,
        "this_p",
        "true");

    // Declare the action struct
    TaskGenerateExecModelActionStruct(m_gen, m_gen->getOutHPrv()).generate(action);


    // Declare the action-init function
    TaskGenerateExecModelActionInit(m_gen, m_gen->getOutC()).generate(action);

    // Define the exec blocks (if present)
    bool body_blocking = false;
    if (action->getExecs(arl::dm::ExecKindT::Body).size()) {
        DEBUG("generate body function");
        std::string fname = m_gen->getNameMap()->getName(action) + "__body";
        std::string tname;
        if ((body_blocking=TaskCheckIsExecBlocking(m_gen->getDebugMgr(), m_gen->isTargetImpBlocking()).check(
            action->getExecs(arl::dm::ExecKindT::Body)))) {
            DEBUG("Body is blocking");
            tname = "struct " + m_gen->getNameMap()->getName(action) + "__body_s";
            m_gen->getOutHPrv()->println("typedef struct %s__body_s {",
                m_gen->getNameMap()->getName(action).c_str());
            m_gen->getOutHPrv()->inc_ind();
            m_gen->getOutHPrv()->println("zsp_rt_task_t task;");
            m_gen->getOutHPrv()->println("%s_t *action;",
                m_gen->getNameMap()->getName(action).c_str());
            m_gen->getOutHPrv()->dec_ind();
            m_gen->getOutHPrv()->println("} %s__body_t;",
                m_gen->getNameMap()->getName(action).c_str());

            TaskGenerateExecModelExecBlockB(
                m_gen, 
                &refgen,
                m_gen->getOutHPrv(),
                m_gen->getOutC()).generate(
                    fname,
                    tname,
                    action->getExecs(arl::dm::ExecKindT::Body));
        } else {
            DEBUG("Body is non-blocking");
            tname = "struct " + m_gen->getNameMap()->getName(action) + "_s";
            TaskGenerateExecModelExecBlockNB(
                m_gen, 
                &refgen,
                m_gen->getOutC()).generate(
                    fname,
                    tname,
                    action->getExecs(arl::dm::ExecKindT::Body));
        }
    }
    if (action->getExecs(arl::dm::ExecKindT::PreSolve).size()) {
        DEBUG("generate pre_solve function");
        std::string fname = m_gen->getNameMap()->getName(action) + "__pre_solve";
        std::string tname = "struct " + m_gen->getNameMap()->getName(action) + "_s";
        TaskGenerateExecModelExecBlockNB(
            m_gen, 
            &refgen,
            m_gen->getOutC()).generate(
                fname,
                tname,
                action->getExecs(arl::dm::ExecKindT::PreSolve));
    }
    if (action->getExecs(arl::dm::ExecKindT::PostSolve).size()) {
        DEBUG("generate post_solve function");
        std::string fname = m_gen->getNameMap()->getName(action) + "__post_solve";
        std::string tname = "struct " + m_gen->getNameMap()->getName(action) + "_s";
        TaskGenerateExecModelExecBlockNB(
            m_gen, 
            &refgen,
            m_gen->getOutC()).generate(
                fname,
                tname,
                action->getExecs(arl::dm::ExecKindT::PostSolve));
    }
    if (arl::dm::TaskActionHasMemClaim().check(action)) {
        TaskGenerateExecModelActionAlloc(m_gen, m_gen->getOutC()).generate(action);
    }

    // Define the activity function if present
    if (action->activities().size()) {
        TaskGenerateExecModelActivity(m_gen).generate(
            action->activities().at(0)->getDataType()
        );
    }


    // Now, declare the action-run function
    m_gen->getOutC()->println("zsp_rt_task_t *%s__run(struct %s_s *actor, struct %s_s *this_p) {",
        m_gen->getNameMap()->getName(action).c_str(),
        m_gen->getActorName().c_str(),
        m_gen->getNameMap()->getName(action).c_str());
    m_gen->getOutC()->inc_ind();
    m_gen->getOutC()->println("zsp_rt_task_t *ret = 0;");
    m_gen->getOutC()->println("");
    m_gen->getOutC()->println("switch (this_p->task.idx) {");
    m_gen->getOutC()->inc_ind();
    m_gen->getOutC()->println("case 0: {");
    m_gen->getOutC()->inc_ind();
    // Declare
    if (action->getExecs(arl::dm::ExecKindT::Body).size()) {
        if (body_blocking) {
            m_gen->getOutC()->println("struct %s__body_s *body = 0;",
                m_gen->getNameMap()->getName(action).c_str());
        }
    } else if (action->activities().size()) {
        m_gen->getOutC()->println("struct activity_%p_s *activity = 0;",
            action->activities().at(0)->getDataType());
    }
    m_gen->getOutC()->println("this_p->task.idx++;");
    if (action->getExecs(arl::dm::ExecKindT::PreSolve).size()) {
        m_gen->getOutC()->println("%s__pre_solve(actor, this_p);",
            m_gen->getNameMap()->getName(action).c_str());
    }
    if (action->getExecs(arl::dm::ExecKindT::PostSolve).size()) {
        m_gen->getOutC()->println("%s__post_solve(actor, this_p);",
            m_gen->getNameMap()->getName(action).c_str());
    }
    if (arl::dm::TaskActionHasMemClaim().check(action)) {
        m_gen->getOutC()->println("%s__alloc(actor, this_p);",
            m_gen->getNameMap()->getName(action).c_str());
    }

    if (action->getExecs(arl::dm::ExecKindT::Body).size()) {
        if (body_blocking) {
            m_gen->getOutC()->println("body = (struct %s__body_s *)zsp_rt_task_enter(",
                m_gen->getNameMap()->getName(action).c_str());
            m_gen->getOutC()->inc_ind();
                m_gen->getOutC()->println("&actor->actor,");
            m_gen->getOutC()->println("sizeof(%s__body_t),",
                m_gen->getNameMap()->getName(action).c_str());
            m_gen->getOutC()->println("(zsp_rt_init_f)&%s__body_init);",
                m_gen->getNameMap()->getName(action).c_str());
            m_gen->getOutC()->dec_ind();
            m_gen->getOutC()->println("if ((ret=zsp_rt_task_run(&actor->actor, &body->task))) {");
            m_gen->getOutC()->inc_ind();
            m_gen->getOutC()->println("break;");
            m_gen->getOutC()->dec_ind();
            m_gen->getOutC()->println("}");
        } else {
            m_gen->getOutC()->println("%s__body(actor, this_p);",
                m_gen->getNameMap()->getName(action).c_str());
        }
    } else if (action->activities().size()) {
        m_gen->getOutC()->println("activity = (struct activity_%p_s *)zsp_rt_task_enter(",
            action->activities().at(0)->getDataType());
        m_gen->getOutC()->inc_ind();
        m_gen->getOutC()->println("&actor->actor,");
        m_gen->getOutC()->println("sizeof(activity_%p_t),",
            action->activities().at(0)->getDataType());
        m_gen->getOutC()->println("(zsp_rt_init_f)&%s_init);",
            m_gen->getNameMap()->getName(action->activities().at(0)->getDataType()).c_str());
        m_gen->getOutC()->dec_ind();
        m_gen->getOutC()->println("if ((ret=zsp_rt_task_run(&actor->actor, &activity->task))) {");
        m_gen->getOutC()->inc_ind();
        m_gen->getOutC()->println("break;");
        m_gen->getOutC()->dec_ind();
        m_gen->getOutC()->println("}");

    }
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");
    m_gen->getOutC()->println("case 1: {");
    m_gen->getOutC()->println("}");
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");
    m_gen->getOutC()->println("return ret;");
    m_gen->getOutC()->dec_ind();
    m_gen->getOutC()->println("}");

    DEBUG_LEAVE("generate");
}

void TaskGenerateExecModelAction::visitDataTypeAction(arl::dm::IDataTypeAction *i) {
    DEBUG_ENTER("visitDataTypeAction");
    if (m_depth == 0) {
        m_depth++;

        // Recurse first to find any sub-types that may 
        // need to be created first
        VisitorBase::visitDataTypeAction(i);

        // Now, declare the type and implement the methods

        m_depth--;
    } else if (!m_gen->fwdDecl(i)) {
        // 
        TaskGenerateExecModelAction(m_gen).generate(i);
    }

    DEBUG_LEAVE("visitDataTypeAction");
}

dmgr::IDebug *TaskGenerateExecModelAction::m_dbg = 0;

}
}
}
