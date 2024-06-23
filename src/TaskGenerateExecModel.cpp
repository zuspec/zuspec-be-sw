/*
 * TaskGenerateExecModel.cpp
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
#include <algorithm>
#include "dmgr/impl/DebugMacros.h"
#include "NameMap.h"
#include "Output.h"
#include "TaskBuildTypeCollection.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelAction.h"
#include "TaskGenerateExecModelComponent.h"
#include "TaskGenerateExecModelFwdDecl.h"
#include "TypeCollection.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModel::TaskGenerateExecModel(
    dmgr::IDebugMgr         *dmgr) : m_dmgr(dmgr) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModel", dmgr);
}

TaskGenerateExecModel::~TaskGenerateExecModel() {

}

void TaskGenerateExecModel::generate(
        arl::dm::IDataTypeComponent     *comp_t,
        arl::dm::IDataTypeAction        *action_t,
        std::ostream                    *out_c,
        std::ostream                    *out_h,
        std::ostream                    *out_h_prv) {
    DEBUG_ENTER("generate");
    m_name_m =  INameMapUP(new NameMap());
    m_out_c = IOutputUP(new Output(out_c, false));
    m_out_h = IOutputUP(new Output(out_h, false));
    m_out_h_prv = IOutputUP(new Output(out_h_prv, false));

    m_action_t = action_t;


    m_actor_name = comp_t->name();
    m_actor_name += "_";
    m_actor_name += action_t->name();
    std::replace(m_actor_name.begin(), m_actor_name.end(), ':', '_');

    m_out_h->println("");

    m_out_h->println("");

    m_out_h_prv->println("");

    TypeCollectionUP type_c(TaskBuildTypeCollection(m_dmgr).build(
        comp_t,
        action_t
    ));

    std::vector<int32_t> sorted = type_c->sort();

    // First, generate forward declarations for all types
    getOutHPrv()->println("struct %s_s;", m_actor_name.c_str());
    for (std::vector<int32_t>::const_iterator
        it=sorted.begin();
        it!=sorted.end(); it++) {
        DEBUG("sorted: id=%d", *it);
        TaskGenerateExecModelFwdDecl(this, getOutHPrv()).generate(type_c->getType(*it));
    }

    // Next, visit each type and generate an implementation
    for (std::vector<int32_t>::const_iterator
        it=sorted.begin();
        it!=sorted.end(); it++) {
        type_c->getType(*it)->accept(m_this);
    }

    // Define top-level actor data-struct
    m_out_h_prv->println("typedef struct %s_s {", getActorName().c_str());
    m_out_h_prv->inc_ind();
    m_out_h_prv->println("zsp_rt_actor_t actor;");
    // public-interface functions go here
    m_out_h_prv->println("%s_t comp;", comp_t->name().c_str());
    m_out_h_prv->dec_ind();
    m_out_h_prv->println("} %s_t;", getActorName().c_str());

    // Declare init function
    m_out_h->println("zsp_rt_actor_t *%s_new();", getActorName().c_str());

    // Define a task for the actor to run
    m_out_c->println("zsp_rt_task_t *%s_actor__run(%s_t *actor, zsp_rt_task_t *task) {",
        getActorName().c_str(),
        getActorName().c_str());
    m_out_c->inc_ind();
    m_out_c->println("zsp_rt_task_t *ret = 0;");
    m_out_c->println("fprintf(stdout, \"actor run %%d\\n\", task->idx);");
    m_out_c->println("switch (task->idx) {");
    m_out_c->inc_ind();
    m_out_c->println("case 0: {");
    m_out_c->inc_ind();
    m_out_c->println("task->idx++;");
    m_out_c->println("ret = task;");
    m_out_c->println("break;");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("case 1: { // initialize comp-tree and start action");
    m_out_c->inc_ind();
    m_out_c->println("task->idx++;");
    m_out_c->println("%s__init(actor, &actor->comp);", comp_t->name().c_str());
    m_out_c->println("ret = task;");
    m_out_c->println("break;");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("case 2: { // done");
    m_out_c->inc_ind();
    m_out_c->println("task->idx++;");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("fprintf(stdout, \"return %%p\\n\", ret);");
    m_out_c->println("return ret;");
    m_out_c->dec_ind();
    m_out_c->println("}");

    // Define a task initialization for the actor task
    m_out_c->println("void %s_actor__init(zsp_rt_actor_t *actor, zsp_rt_task_t *task) {",
        getActorName().c_str());
    m_out_c->inc_ind();
    m_out_c->println("fprintf(stdout, \"actor init\\n\");");
    m_out_c->println("task->func = (zsp_rt_task_f)&%s_actor__run;", getActorName().c_str());
    m_out_c->dec_ind();
    m_out_c->println("}");

    // Define init function
    m_out_c->println("zsp_rt_actor_t *%s_new() {", getActorName().c_str());
    m_out_c->inc_ind();
    m_out_c->println("zsp_rt_task_t *task;");
    m_out_c->println("%s_t *actor = (%s_t *)malloc(sizeof(%s_t));",
        getActorName().c_str(),
        getActorName().c_str(),
        getActorName().c_str());
    m_out_c->println("zsp_rt_actor_init(&actor->actor);");

    // Now, create a task that will initialize the component tree
    // and run the root action
    m_out_c->println("task = zsp_rt_task_enter(");
    m_out_c->inc_ind();
    m_out_c->println("&actor->actor,");
    m_out_c->println("sizeof(zsp_rt_task_t),");
    m_out_c->println("&%s_actor__init);", getActorName().c_str());
    m_out_c->dec_ind();
    m_out_c->println("");
    m_out_c->println("task = zsp_rt_task_run(");
    m_out_c->inc_ind();
    m_out_c->println("&actor->actor,");
    m_out_c->println("task);");
    m_out_c->dec_ind();
    m_out_c->println("zsp_rt_queue_task(&actor->actor, task);");
    m_out_c->println("");
    m_out_c->println("return (zsp_rt_actor_t *)actor;");
    m_out_c->dec_ind();
    m_out_c->println("}");


    m_out_h->println("");
    m_out_h_prv->println("");
    DEBUG_LEAVE("generate");
}

bool TaskGenerateExecModel::fwdDecl(vsc::dm::IDataType *dt, bool add) {
    std::unordered_set<vsc::dm::IDataType *>::const_iterator it;

    if ((it=m_dt_fwd_decl.find(dt)) == m_dt_fwd_decl.end()) {
        if (add) {
            m_dt_fwd_decl.insert(dt);
        }
        return false;
    } else {
        return true;
    }
}

void TaskGenerateExecModel::visitDataTypeAction(arl::dm::IDataTypeAction *i) { 
    DEBUG_ENTER("visitDataTypeAction");
    TaskGenerateExecModelAction(this, (i==m_action_t)).generate(i);
    DEBUG_LEAVE("visitDataTypeAction");
}

void TaskGenerateExecModel::visitDataTypeActivity(arl::dm::IDataTypeActivity *t) { }

void TaskGenerateExecModel::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) { 
    DEBUG_ENTER("visitDataTypeComponent");
    TaskGenerateExecModelComponent(this).generate(t);
    DEBUG_LEAVE("visitDataTypeComponent");
}

void TaskGenerateExecModel::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) { }

dmgr::IDebug *TaskGenerateExecModel::m_dbg = 0;

}
}
}
