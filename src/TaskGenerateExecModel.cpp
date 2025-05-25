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
#include "ITaskGenerateExecModelCustomGen.h"
#include "NameMap.h"
#include "Output.h"
#include "TaskBuildTypeCollection.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateExecModelAddrHandle.h"
#include "TaskGenerateExecModelCoreMethodCall.h"
#include "TaskGenerateExecModelMemRwCall.h"
#include "TaskGenerateExecModelRegRwCall.h"
#include "TaskGenerateExecModelAction.h"
#include "TaskGenerateExecModelActivity.h"
#include "TaskGenerateComp.h"
#include "TaskGenerateExecModelDefineType.h"
#include "TaskGenerateExecModelFwdDecl.h"
#include "TaskGenerateStruct.h"
#include "TypeCollection.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateExecModel::TaskGenerateExecModel(
    arl::dm::IContext       *ctxt) : m_ctxt(ctxt), m_dmgr(ctxt->getDebugMgr()),
    m_target_imp_blocking(false) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateExecModel", m_dmgr);
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

    attach_custom_gen();

    m_comp_t = comp_t;
    m_action_t = action_t;

    m_num_aspace_insts = TaskCountAspaceInstances().count(comp_t);
    DEBUG("AddressSpace Instances: %d", m_num_aspace_insts);
    m_comp_tree_m = TaskBuildStaticCompTreeMap(m_dmgr).build(comp_t);
    m_addr_trait_m = TaskCollectAddrTraitTypes(getDebugMgr()).collect(m_comp_t);

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

    // Core model-centric definitions first
    core_defs();

    // First, generate forward declarations for all types
    getOutHPrv()->println("struct %s_s;", m_actor_name.c_str());
    for (std::vector<int32_t>::const_iterator
        it=sorted.begin();
        it!=sorted.end(); it++) {
        TaskGenerateExecModelFwdDecl(this, getOutHPrv()).generate(
            type_c->getType(*it));
        getOutHPrv()->println("");
    }

    // Next, visit each type and generate an implementation
    for (std::vector<int32_t>::const_iterator
        it=sorted.begin();
        it!=sorted.end(); it++) {
        TaskGenerateExecModelDefineType(this, getOutHPrv(), getOutC()).generate(
            type_c->getType(*it));
        getOutHPrv()->println("");
    }

    generate_actor_entry();

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

void TaskGenerateExecModel::core_defs() {
    std::string trait_idx_t;
    std::string comp_idx_t;

    if (m_num_aspace_insts >= (1ULL << 32)) {
        trait_idx_t = "uint64_t";
    } else if (m_num_aspace_insts >= (1ULL << 16)) {
        trait_idx_t = "uint32_t";
    } else if (m_num_aspace_insts >= (1ULL << 8)) {
        trait_idx_t = "uint16_t";
    } else {
        trait_idx_t = "uint8_t";
    }

    m_out_h_prv->println("typedef %s zsp_rt_aspace_idx_t;", trait_idx_t.c_str());

    if (m_comp_tree_m.first >= (1ULL << 32)) {
        comp_idx_t = "uint64_t";
    } else if (m_comp_tree_m.first >= (1ULL << 16)) {
        comp_idx_t = "uint32_t";
    } else if (m_comp_tree_m.first >= (1ULL << 8)) {
        comp_idx_t = "uint16_t";
    } else {
        comp_idx_t = "uint8_t";
    }

    m_out_h_prv->println("typedef %s zsp_rt_comp_idx_t;", comp_idx_t.c_str());

    m_out_h_prv->println("typedef struct %s_init_s {", getActorName().c_str());
    m_out_h_prv->inc_ind();
    m_out_h_prv->println("zsp_rt_aspace_idx_t       aspace_idx;");
    m_out_h_prv->println("zsp_rt_comp_idx_t         comp_idx;");
    m_out_h_prv->println("zsp_rt_aspace_idx_t       traits[%d];", m_addr_trait_m.size());
    m_out_h_prv->dec_ind();
    m_out_h_prv->println("} %s_init_t;", getActorName().c_str());

}


void TaskGenerateExecModel::generate_actor_entry() {
    DEBUG_ENTER("generate_actor_entry");
    // Define top-level actor data-struct
    m_out_h_prv->println("typedef struct %s_s {", getActorName().c_str());
    m_out_h_prv->inc_ind();
    m_out_h_prv->println("zsp_rt_actor_t actor;");
    // public-interface functions go here
    m_out_h_prv->println("%s_t comp;", m_comp_t->name().c_str());
    m_out_h_prv->println("zsp_rt_component_t *comp_insts[%d];", m_comp_tree_m.first);
    m_out_h_prv->println("zsp_rt_addr_space_t *aspace_insts[%d];", m_num_aspace_insts);
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
    m_out_c->println("case 0: { // Always yield");
    m_out_c->inc_ind();
    m_out_c->println("task->idx++;");
    m_out_c->println("ret = task;");
    m_out_c->println("break;");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("case 1: { // initialize comp-tree and start action");
    m_out_c->inc_ind();
    m_out_c->println("%s_init_t init_data;", getActorName().c_str());
    m_out_c->println("%s_t *action_t = (%s_t *)zsp_rt_task_enter(",
        getNameMap()->getName(m_action_t).c_str(),
        getNameMap()->getName(m_action_t).c_str());
    m_out_c->inc_ind();
    m_out_c->println("&actor->actor,");
    m_out_c->println("sizeof(%s_t),", getNameMap()->getName(m_action_t).c_str());
    m_out_c->println("(zsp_rt_init_f)&%s__init);",
        getNameMap()->getName(m_action_t).c_str());
    m_out_c->dec_ind();
    m_out_c->println("task->idx++;");
    m_out_c->println("init_data.aspace_idx = 0;");
    m_out_c->println("init_data.comp_idx = 0;");
    m_out_c->println("%s__exec_init(actor, &init_data, actor->comp.__aspace, &actor->comp);", m_comp_t->name().c_str());
    m_out_c->println("action_t->comp = &actor->comp;");
    m_out_c->println("ret = zsp_rt_task_run(&actor->actor, &action_t->task);");
    m_out_c->println("if (ret) {");
    m_out_c->inc_ind();
    m_out_c->println("zsp_rt_queue_task(&actor->actor, ret);");
    m_out_c->println("break;");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->dec_ind();
    m_out_c->println("}");
    m_out_c->println("case 2: { // done");
    m_out_c->inc_ind();
    m_out_c->println("task->idx++;");
    m_out_c->println("// TODO: call action dtor");
    m_out_c->println("fprintf(stdout, \"task->prev=%%p\\n\", task->prev);");
    m_out_c->println("task->prev->rc.dtor((zsp_rt_actor_t *)actor, (zsp_rt_rc_t *)task->prev);");
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
//    m_out_c->println("fprintf(stdout, \"actor init\\n\");");
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
    m_out_c->println("(zsp_rt_init_f)&%s_actor__init);", getActorName().c_str());
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

    DEBUG_LEAVE("generate_actor_entry");
}

void TaskGenerateExecModel::attach_custom_gen() {
    DEBUG_ENTER("attach_custom_gen");

    vsc::dm::IDataTypeStruct *addr_handle_t = m_ctxt->findDataTypeStruct(
        "addr_reg_pkg::addr_handle_t");
    m_name_m->setName(addr_handle_t, "zsp_rt_addr_handle");
    addr_handle_t->setAssociatedData(new TaskGenerateExecModelAddrHandle(getDebugMgr()));
    m_addr_handle_t = addr_handle_t;

    arl::dm::IDataTypeFunction *f_t;
    f_t = m_ctxt->findDataTypeFunction("addr_reg_pkg::make_handle_from_handle");
    m_name_m->setName(f_t, "zsp_rt_make_handle_from_handle");
    // f_t->setAssociatedData(
    //     new TaskGenerateExecModelCoreMethodCall(
    //         m_dmgr,
    //         "zsp_rt_make_handle_from_handle",
    //         0,
    //         {"zsp_rt_addr_claim_t *"}));

    f_t = m_ctxt->findDataTypeFunction("addr_reg_pkg::make_handle_from_claim");
    m_name_m->setName(f_t, "zsp_rt_make_handle_from_claim");
    f_t->setAssociatedData(
        new TaskGenerateExecModelCoreMethodCall(
            m_dmgr,
            "zsp_rt_make_handle_from_claim",
            0,
            {"zsp_rt_addr_claimspec_t *"}));

    std::vector<std::string> rw_funcs = {
        "addr_reg_pkg::write64",
        "addr_reg_pkg::write32",
        "addr_reg_pkg::write16",
        "addr_reg_pkg::write8",
        "addr_reg_pkg::read64",
        "addr_reg_pkg::read32",
        "addr_reg_pkg::read16",
        "addr_reg_pkg::read8"
    };
    for (std::vector<std::string>::const_iterator
        it=rw_funcs.begin();
        it!=rw_funcs.end(); it++) {
        f_t = m_ctxt->findDataTypeFunction(*it);
        f_t->setAssociatedData(new TaskGenerateExecModelMemRwCall(m_dmgr));
    }

    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=m_ctxt->getDataTypeStructs().begin();
        it!=m_ctxt->getDataTypeStructs().end(); it++) {
        const std::string &name = (*it)->name();

        if (name.find("::contiguous_addr_space_c") != -1 
            || name.find("::transparent_addr_space_c") != -1) {
//            m_name_m->setName(it->get(), "zsp_rt_addr_space");
        }
    }

    for (std::vector<arl::dm::IDataTypeFunction *>::const_iterator
        it=m_ctxt->getDataTypeFunctions().begin();
        it!=m_ctxt->getDataTypeFunctions().end(); it++) {
        std::string name = (*it)->name();
        DEBUG("name: %s", name.c_str());
        if (name.find("addr_reg_pkg::") == 0) {
            if (name.find("::addr_handle_t") != -1) {

            } else if (name.find("::contiguous_addr_space_c") != -1 
                || name.find("::transparent_addr_space_c") != -1) {
                std::string rt_name = (name.find("add_region") != -1)?
                    "zsp_rt_addr_space_add_region":
                    "zsp_rt_addr_space_add_nonallocatable_region";

                (*it)->setAssociatedData(
                    new TaskGenerateExecModelCoreMethodCall(
                        m_dmgr,
                        rt_name,
                        0,
                        {"zsp_rt_addr_space_t *", "zsp_rt_addr_region_t *"}));
            } else if (name.find("::reg_group_c") != -1) {
                if (name.find("set_handle") != -1) {
                    (*it)->setAssociatedData(
                        new TaskGenerateExecModelCoreMethodCall(
                            m_dmgr,
                            "zsp_rt_reg_group_set_handle",
                            0,
                            {"void **"}));
                }
                std::string rt_name = (name.find("add_region") != -1)?
                    "zsp_rt_addr_space_add_region":
                    "zsp_rt_addr_space_add_nonallocatable_region";
            } else if (name.find("::reg_c") != -1) {
                DEBUG("Attach reg-access generator");
                (*it)->setAssociatedData(
                    new TaskGenerateExecModelRegRwCall(m_dmgr));
            }
        } else if (name.find("std_pkg::") == 0) {
            if (name.find("urandom_range") != -1) {
                (*it)->setAssociatedData(
                    new TaskGenerateExecModelCoreMethodCall(
                        m_dmgr,
                        "zsp_rt_urandom_range",
                        -1, {}));
            } else if (name.find("urandom") != -1) {
                (*it)->setAssociatedData(
                    new TaskGenerateExecModelCoreMethodCall(
                        m_dmgr,
                        "zsp_rt_urandom",
                        -1, {}));
            }
        }
    }

    DEBUG_LEAVE("attach_custom_gen");
}

dmgr::IDebug *TaskGenerateExecModel::m_dbg = 0;

}
}
}
