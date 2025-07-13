/*
 * TaskGenerateAction.cpp
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
#include "TaskGenerateAction.h"
#include "TaskGenerateActionAlloc.h"
#include "TaskGenerateActionInit.h"
#include "TaskGenerateActionDtor.h"
#include "TaskGenerateActionStruct.h"
#include "TaskGenerateActionType.h"
#include "TaskGenerateExecModelActivity.h"
#include "TaskGenerateExecBlockB.h"
#include "TaskGenerateExecBlockNB.h"
#include "TaskGenerateExecBlockB.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateAction::TaskGenerateAction(
        IContext                    *ctxt,
        TypeInfo                    *type_info,
        IOutput                     *out_h,
        IOutput                     *out_c) : 
        TaskGenerateStruct(ctxt, type_info, out_h, out_c), m_is_root(true), m_depth(0) {
    m_dbg = 0;
    DEBUG_INIT("zsp::be::sw::TaskGenerateAction", ctxt->getDebugMgr());
}

TaskGenerateAction::~TaskGenerateAction() {

}

void TaskGenerateAction::generate_type(
    vsc::dm::IDataTypeStruct    *t,
    IOutput                     *out_h,
    IOutput                     *out_c) {
    DEBUG_ENTER("generate_type");
    TaskGenerateActionType(m_ctxt, m_out_h, m_out_c).generate(t);
    DEBUG_LEAVE("generate_type");
}

void TaskGenerateAction::generate_exec_blocks(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    zsp::arl::dm::IDataTypeAction *action_t = dynamic_cast<zsp::arl::dm::IDataTypeAction *>(t);
    DEBUG_ENTER("generate_exec_blocks");

    // First, generate common exec blocks
    TaskGenerateStruct::generate_exec_blocks(t, out);

    if (action_t->activities().size()) {
        DEBUG("generate activity function");
//        TaskGenerateExecModelActivity(m_ctxt, m_out_h, m_out_c).generate(action_t);
    } else {

        GenRefExprExecModel refgen(m_ctxt->getDebugMgr(), t, "this_p", true, "(*__locals)");
        const std::vector<arl::dm::ITypeExecUP> &execs = action_t->getExecs(arl::dm::ExecKindT::Body);
        DEBUG("%d execs for body", execs.size());
        std::string tname = m_ctxt->nameMap()->getName(t);
        std::string fname = tname + "__body";
        TaskGenerateExecBlockB(m_ctxt, &refgen, m_out_h, m_out_c).generate(
            fname,
            tname,
            execs);
    }


    DEBUG_LEAVE("generate_exec_blocks");
}

/*
void TaskGenerateAction::generate_init(
    vsc::dm::IDataTypeStruct    *t,
    IOutput                     *out_h,
    IOutput                     *out_c) {
    DEBUG_ENTER("generate_init");
    TaskGenerateStructInit(m_ctxt, m_out_h, m_out_c).generate(t);
    DEBUG_LEAVE("generate_init");
}
 */

#ifdef UNDEFINED
void TaskGenerateAction::generate(arl::dm::IDataTypeAction *action) {
    DEBUG_ENTER("generate");
    GenRefExprExecModel refgen(
        m_ctxt->getDebugMgr(),
        action,
        "this_p",
        "true");

    // Declare the action struct
//    TaskGenerateActionStruct(m_ctxt, m_out_h).generate(action);


    // Declare the action-init function
    TaskGenerateActionInit(m_ctxt, m_out_h, m_out_c).generate(action);

    // Define the exec blocks (if present)
    bool body_blocking = false;
    if (action->getExecs(arl::dm::ExecKindT::Body).size()) {
        DEBUG("generate body function");
        std::string fname = m_ctxt->nameMap()->getName(action) + "__body";
        std::string tname;
        if ((body_blocking=TaskCheckIsExecBlocking(
            m_ctxt->getDebugMgr(), true /*m_gen->isTargetImpBlocking()*/).check(
            action->getExecs(arl::dm::ExecKindT::Body)))) {
            DEBUG("Body is blocking");
            tname = "struct " + m_ctxt->nameMap()->getName(action) + "__body_s";
            m_out_h->println("typedef struct %s__body_s {",
                m_ctxt->nameMap()->getName(action).c_str());
            m_out_h->inc_ind();
            m_out_h->println("zsp_rt_task_t task;");
            m_out_h->println("%s_t *action;",
                m_ctxt->nameMap()->getName(action).c_str());
            m_out_h->dec_ind();
            m_out_h->println("} %s__body_t;",
                m_ctxt->nameMap()->getName(action).c_str());

            TaskGenerateExecModelExecBlockB(
                0, // m_gen, 
                &refgen,
                m_out_h,
                m_out_c).generate(
                    fname,
                    tname,
                    action->getExecs(arl::dm::ExecKindT::Body));
        } else {
            DEBUG("Body is non-blocking");
            tname = "struct " + m_ctxt->nameMap()->getName(action) + "_s";
            // TaskGenerateExecModelExecBlockNB(
            //     m_gen, 
            //     &refgen,
            //     m_out_c).generate(
            //         fname,
            //         tname,
            //         action->getExecs(arl::dm::ExecKindT::Body));
        }
    }
    if (action->getExecs(arl::dm::ExecKindT::PreSolve).size()) {
        DEBUG("generate pre_solve function");
        std::string fname = m_ctxt->nameMap()->getName(action) + "__pre_solve";
        std::string tname = "struct " + m_ctxt->nameMap()->getName(action) + "_s";
        // TaskGenerateExecModelExecBlockNB(
        //     m_gen, 
        //     &refgen,
        //     m_out_c).generate(
        //         fname,
        //         tname,
        //         action->getExecs(arl::dm::ExecKindT::PreSolve));
    }
    if (action->getExecs(arl::dm::ExecKindT::PostSolve).size()) {
        DEBUG("generate post_solve function");
        std::string fname = m_ctxt->nameMap()->getName(action) + "__post_solve";
        std::string tname = "struct " + m_ctxt->nameMap()->getName(action) + "_s";
        // TaskGenerateExecModelExecBlockNB(
        //     m_gen, 
        //     &refgen,
        //     m_out_c).generate(
        //         fname,
        //         tname,
        //         action->getExecs(arl::dm::ExecKindT::PostSolve));
    }
    if (arl::dm::TaskActionHasMemClaim().check(action)) {
        TaskGenerateActionAlloc(m_ctxt, m_type_info, m_out_h, m_out_c).generate(action);
    }

    // Define the activity function if present
    if (action->activities().size()) {
        TaskGenerateExecModelActivity(0 /*m_gen*/).generate(
            action->activities().at(0)->getDataType()
        );
    }


    // Now, declare the action-run function
    m_out_c->println("zsp_rt_task_t *%s__run(struct %s_s *actor, struct %s_s *this_p) {",
        m_ctxt->nameMap()->getName(action).c_str(),
        "abc" /*m_gen->getActorName().c_str() */,
        m_ctxt->nameMap()->getName(action).c_str());
    m_out_c->inc_ind();
    m_out_c->println("zsp_rt_task_t *ret = 0;");
    m_out_c->println("");
    m_out_c->println("switch (this_p->task.idx) {");
    m_out_c->inc_ind();
    m_out_c->println("case 0: {");
    m_out_c->inc_ind();
    // Declare
    if (action->getExecs(arl::dm::ExecKindT::Body).size()) {
        if (body_blocking) {
            m_out_c->println("struct %s__body_s *body = 0;",
                m_ctxt->nameMap()->getName(action).c_str());
        }
    } else if (action->activities().size()) {
        m_out_c->println("struct activity_%p_s *activity = 0;",
            action->activities().at(0)->getDataType());
    }
    m_out_c->println("this_p->task.idx++;");
    if (action->getExecs(arl::dm::ExecKindT::PreSolve).size()) {
        m_out_c->println("%s__pre_solve(actor, this_p);",
            m_ctxt->nameMap()->getName(action).c_str());
    }
    if (action->getExecs(arl::dm::ExecKindT::PostSolve).size()) {
        m_out_c->println("%s__post_solve(actor, this_p);",
            m_ctxt->nameMap()->getName(action).c_str());
    }
    if (arl::dm::TaskActionHasMemClaim().check(action)) {
        m_out_c->println("%s__alloc(actor, this_p);",
            m_ctxt->nameMap()->getName(action).c_str());
    }

    if (action->getExecs(arl::dm::ExecKindT::Body).size()) {
        if (body_blocking) {
            m_out_c->println("body = (struct %s__body_s *)zsp_rt_task_enter(",
                m_ctxt->nameMap()->getName(action).c_str());
            m_out_c->inc_ind();
                m_out_c->println("&actor->actor,");
            m_out_c->println("sizeof(%s__body_t),",
                m_ctxt->nameMap()->getName(action).c_str());
            m_out_c->println("(zsp_rt_init_f)&%s__body_init);",
                m_ctxt->nameMap()->getName(action).c_str());
            m_out_c->dec_ind();
            m_out_c->println("if ((ret=zsp_rt_task_run(&actor->actor, &body->task))) {");
            m_out_c->inc_ind();
            m_out_c->println("break;");
            m_out_c->dec_ind();
            m_out_c->println("}");
        } else {
            m_out_c->println("%s__body(actor, this_p);",
                m_ctxt->nameMap()->getName(action).c_str());
        }
    } else if (action->activities().size()) {
        m_out_c->println("activity = (struct activity_%p_s *)zsp_rt_task_enter(",
            action->activities().at(0)->getDataType());
        m_out_c->inc_ind();
        m_out_c->println("&actor->actor,");
        m_out_c->println("sizeof(activity_%p_t),",
            action->activities().at(0)->getDataType());
        m_out_c->println("(zsp_rt_init_f)&%s_init);",
            m_ctxt->nameMap()->getName(action->activities().at(0)->getDataType()).c_str());
        m_out_c->dec_ind();
        m_out_c->println("if ((ret=zsp_rt_task_run(&actor->actor, &activity->task))) {");
        m_out_c->inc_ind();
        m_out_c->println("break;");
        m_out_c->dec_ind();
        m_out_c->println("}");

    }
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("case 1: {");
    m_out_c->println("}");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("return ret;");
    m_out_c->dec_ind();
    m_out_c->println("}");

    // Finally, define the destructor
    TaskGenerateActionDtor(
        m_ctxt, 
        m_out_h,
        m_out_c).generate(action);

    DEBUG_LEAVE("generate");
}

#endif /* UNDEFINED */

#ifdef UNDEFINED
void TaskGenerateAction::visitDataTypeAction(arl::dm::IDataTypeAction *i) {
    DEBUG_ENTER("visitDataTypeAction");
    if (m_depth == 0) {
        m_depth++;

        // Recurse first to find any sub-types that may 
        // need to be created first
        VisitorBase::visitDataTypeAction(i);

        // Now, declare the type and implement the methods

        m_depth--;
    } /** else if (!m_gen->fwdDecl(i)) {
        // 
        TaskGenerateAction(m_gen).generate(i);
    } */

    DEBUG_LEAVE("visitDataTypeAction");
}
#endif /* UNDEFINED */


}
}
}
