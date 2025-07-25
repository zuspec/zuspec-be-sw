/*
 * TaskGenerateModel.cpp
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
#include <fstream>
#include "dmgr/impl/DebugMacros.h"
#include "CustomGenImportCall.h"
#include "TaskGatherCompTypes.h"
#include "TaskGatherTypes.h"
#include "TaskGenerateActor.h"
#include "TaskGenerateModel.h"
#include "TaskGenerateType.h"
#include "TaskGenerateImportApi.h"
#include "TaskGenerateExecModelAddrHandle.h"
#include "FileUtil.h"
#include "Output.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateModel::TaskGenerateModel(
    IContext            *ctxt,
    const std::string   &outdir) : m_ctxt(ctxt), m_outdir(outdir) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateModel", ctxt->getDebugMgr());
}

TaskGenerateModel::~TaskGenerateModel() {

}

void TaskGenerateModel::generate(
    arl::dm::IDataTypeComponent                     *pss_top,
    const std::vector<arl::dm::IDataTypeAction *>   &actions) {
    DEBUG_ENTER("generate");
    std::vector<vsc::dm::IAccept *> actions_l;
//    m_ctxt->setModelName(m_name);

    attach_custom_gen();

    FileUtil::mkdirs(m_outdir);

    // std::vector<arl::dm::IDataTypeComponent *> comp_types;

    // TaskGatherCompTypes(m_ctxt).gather(pss_top, comp_types);

    // for (std::vector<arl::dm::IDataTypeComponent *>::const_iterator
    //     it=comp_types.begin();
    //     it!=comp_types.end(); it++) {
    //     std::string basename = m_outdir + "/";
    //     basename += m_ctxt->nameMap()->getName(*it);

    //     std::ofstream out_c(basename + ".c");
    //     std::ofstream out_h(basename + ".h");

    //     TaskGenerateType(m_ctxt, &out_h, &out_c).generate(*it);
    //     out_c.close();
    //     out_h.close();
    // }

    // TODO: must find root actions in the scope of root component
    if (!actions.size()) {
        // TODO: go find exported actions
    } else {
        actions_l.insert(
            actions_l.begin(), 
            actions.begin(),
            actions.end());
    }

    TaskGatherTypes types(m_ctxt);

    DEBUG_ENTER("Struct types:");
    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeStructs().begin();
        it!=m_ctxt->ctxt()->getDataTypeStructs().end(); it++) {
        DEBUG("Struct: %s", (*it)->name().c_str());
    }
    DEBUG_LEAVE("Struct types:");

    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeStructs().begin();
        it!=m_ctxt->ctxt()->getDataTypeStructs().end(); it++) {
        types.gather(it->get());
    }

    // TODO: Generate the import API
    // - Re-iterate core functions for simplicity
    //
    // TODO: Generate library entry-point functions
    // - 

    for (std::vector<vsc::dm::IDataTypeStruct *>::const_iterator
        it=types.types().begin();
        it!=types.types().end(); it++) {
        const std::string &name = (*it)->name();
        std::string basename = m_outdir + "/";
        basename += m_ctxt->nameMap()->getName(*it);

        DEBUG("Generating type: %s", basename.c_str());

        std::ofstream os_c(basename + ".c");
        std::ofstream os_h(basename + ".h");
        IOutputUP out_c(new Output(&os_c, false));
        IOutputUP out_h(new Output(&os_h, false));

        ITaskGenerateExecModelCustomGen *gen = 
            dynamic_cast<ITaskGenerateExecModelCustomGen *>(
                (*it)->getAssociatedData()
            );
        if (gen) {
            DEBUG("Type %s has a custom generator", (*it)->name().c_str());
            if (!gen->hasFlags(ITaskGenerateExecModelCustomGen::Flags::Builtin)) {
                DEBUG("Calling generator");
                gen->genDefinition(m_ctxt, out_h.get(), out_c.get(), *it);
            } else {
                DEBUG("Built-in type");
            }
        } else {
            DEBUG("Type %s does not have a custom generator", (*it)->name().c_str());
            TaskGenerateType(m_ctxt, out_h.get(), out_c.get()).generate(*it);
        }
        out_c->close();
        out_h->close();
        os_c.close();
        os_h.close();
    }

    generate_interface();

    generate_api();

    DEBUG_LEAVE("generate");
}

void TaskGenerateModel::attach_custom_gen() {
    DEBUG_ENTER("attach_custom_gen %d structs ; %d functions",
        m_ctxt->ctxt()->getDataTypeStructs().size(),
        m_ctxt->ctxt()->getDataTypeFunctions().size());

    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeStructs().begin();
        it!=m_ctxt->ctxt()->getDataTypeStructs().end(); it++) {
        const std::string &name = (*it)->name();
        DEBUG("Struct: %s", name.c_str());

        if (name.find("addr_reg_pkg::") == 0) {
            int len = std::string("addr_reg_pkg::").size();
            const std::string leaf = name.substr(len);

            DEBUG("addr_reg_pkg: leaf=%s", leaf.c_str());

            if (leaf == "addr_handle_t") {
                DEBUG("Attach addr_handle_t generator data");
                (*it)->setAssociatedData(
                    new TaskGenerateExecModelAddrHandle(m_ctxt->getDebugMgr()));
            }
        }
    }

    for (std::vector<arl::dm::IDataTypeFunction *>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeFunctions().begin();
        it!=m_ctxt->ctxt()->getDataTypeFunctions().end(); it++) {
        const std::string &name = (*it)->name();
        DEBUG("Function: %s ; flags=0x%08x", name.c_str(), (*it)->getFlags());

        if (name.find("addr_reg_pkg::") == 0) {
            int len = std::string("addr_reg_pkg::").size();
            const std::string leaf = name.substr(len);

        } else if (name.find("std_pkg::") == 0) {
            if (name.find("::print") > 0 || name.find("::message")) {
                // These methods are implemented externally
                (*it)->setAssociatedData(new CustomGenImportCall(m_ctxt->getDebugMgr()));
            }
        } else {
            // Non-core imports are all handled the same
            if ((*it)->hasFlags(arl::dm::DataTypeFunctionFlags::Import) &&
                !(*it)->hasFlags(arl::dm::DataTypeFunctionFlags::Core)) {
                (*it)->setAssociatedData(new CustomGenImportCall(m_ctxt->getDebugMgr()));
            }
        }
    }

    DEBUG_LEAVE("attach_custom_gen");
}

void TaskGenerateModel::visitDataTypeAction(arl::dm::IDataTypeAction *t) {
    if (m_kind == kind_e::ACTION or m_kind == kind_e::BOTH) {
        const std::string &name = t->name();
        if (name.find("executor_pkg::") == -1 && name.find("addr_reg_pkg::") == -1) {
            switch (m_mode) {
                case mode_e::COUNT: m_count++; break;
                case mode_e::INCLUDE: m_out->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(t).c_str()); break;
                case mode_e::GETTYPE: m_out->println("*(at_p++) = (zsp_action_type_t *)%s__type();", m_ctxt->nameMap()->getName(t).c_str()); break;
            }
        }
    }
}

void TaskGenerateModel::visitDataTypeComponent(arl::dm::IDataTypeComponent *t) {
    if (m_kind == kind_e::COMPONENT or m_kind == kind_e::BOTH) {
        const std::string &name = t->name();
        if (name.find("executor_pkg::") == -1 && name.find("addr_reg_pkg::") == -1) {
            switch (m_mode) {
                case mode_e::COUNT: m_count++; break;
                case mode_e::INCLUDE: m_out->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(t).c_str()); break;
                case mode_e::GETTYPE: m_out->println("*(ct_p++) = (zsp_component_type_t *)%s__type();", m_ctxt->nameMap()->getName(t).c_str()); break;
            }
        }
    }
}

void TaskGenerateModel::generate_interface() {
    // // First, generate an actor for each...
    // for (std::vector<vsc::dm::IAccept *>::const_iterator
    //     it=actors.begin();
    //     it!=actors.end(); it++) {
    //     if (dynamic_cast<arl::dm::IDataTypeAction *>(*it)) {
    //         arl::dm::IDataTypeAction *action = dynamic_cast<arl::dm::IDataTypeAction *>(*it);
    //         std::string name = action->name();
    //         std::replace(name.begin(), name.end(), ':', '_');

    //         std::ofstream out_cs(m_outdir + "/" + name + "_actor.c");
    //         std::ofstream out_hs(m_outdir + "/" + name + "_actor.h");
    //         IOutputUP out_c(new Output(&out_cs, false));
    //         IOutputUP out_h(new Output(&out_hs, false));

    //         TaskGenerateActor(m_ctxt, out_h.get(), out_c.get()).generate(pss_top, action);
    //     }
    // }

    std::ofstream out_cs(m_outdir + "/model.c");
    std::ofstream out_hs(m_outdir + "/model.h");

    IOutputUP out_c(new Output(&out_cs, false));
    IOutputUP out_h(new Output(&out_hs, false));

    // Generate the interface method prototypes
    out_h->println("#ifndef INCLUDED_MODEL_H");
    out_h->println("#define INCLUDED_MODEL_H");
    out_h->println("#include \"zsp/be/sw/rt/zsp_actor.h\"");
    out_h->println("#include \"zsp/be/sw/rt/zsp_model.h\"");
    out_h->println("#include \"model_api.h\"");

    out_h->println("#ifdef __cplusplus");
    out_h->println("extern \"C\" {");
    out_h->println("#endif");
    out_h->println("");
    out_h->println("zsp_model_t *pss_model();");
    out_h->println("");
    out_h->println("#ifdef __cplusplus");
    out_h->println("}");
    out_h->println("#endif");

    out_h->println("#endif /* INCLUDED_MODEL_H */");

    out_c->println("#include \"model.h\"");
    // Generate includes for each component and action
    m_mode = mode_e::INCLUDE;
    m_kind = kind_e::BOTH;
    m_out = out_c.get();
    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeStructs().begin();
        it!=m_ctxt->ctxt()->getDataTypeStructs().end(); it++) {
        (*it)->accept(m_this);
    }

    m_mode = mode_e::COUNT;
    m_kind = kind_e::ACTION;
    m_count = 0;
    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeStructs().begin();
        it!=m_ctxt->ctxt()->getDataTypeStructs().end(); it++) {
        (*it)->accept(m_this);
    }
    int32_t n_action_t = m_count;

    m_mode = mode_e::COUNT;
    m_kind = kind_e::COMPONENT;
    m_count = 0;
    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeStructs().begin();
        it!=m_ctxt->ctxt()->getDataTypeStructs().end(); it++) {
        (*it)->accept(m_this);
    }
    int32_t n_comp_t = m_count;

    out_c->println("");
    out_c->println("zsp_model_t *pss_model() {");
    out_c->inc_ind();
    out_c->println("extern const char **model_get_import_types();");
    out_c->println("static zsp_action_type_t *action_t[%d+1];", n_action_t);
    out_c->println("static zsp_component_type_t *comp_t[%d+1];", n_comp_t);
    out_c->println("static zsp_model_t model = {.action_types = action_t, .comp_types = comp_t};");
    out_c->println("static int initialized = 0;");
    out_c->println("if (!initialized) {");
    out_c->inc_ind();
    out_c->println("zsp_action_type_t **at_p = action_t;");
    out_c->println("zsp_component_type_t **ct_p = comp_t;");
    out_c->println("initialized = 1;");

    out_c->println("");
    out_c->println("model.methods = model_get_import_types();");
    out_c->println("");
    out_c->println("action_t[%d] = 0;", n_action_t);
    out_c->println("comp_t[%d] = 0;", n_comp_t);
    out_c->println("");


    m_mode = mode_e::GETTYPE;
    m_kind = kind_e::BOTH;
    m_out = out_c.get();
    for (std::vector<vsc::dm::IDataTypeStructUP>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeStructs().begin();
        it!=m_ctxt->ctxt()->getDataTypeStructs().end(); it++) {
        (*it)->accept(m_this);
    }

    out_c->dec_ind();
    out_c->println("}");
    out_c->println("return &model;");
    out_c->dec_ind();
    out_c->println("}");

    out_c->close();
    out_h->close();
}

void TaskGenerateModel::generate_api() {
    std::ofstream out_cs(m_outdir + "/model_api.c");
    std::ofstream out_hs(m_outdir + "/model_api.h");

    IOutputUP out_c(new Output(&out_cs, false));
    IOutputUP out_h(new Output(&out_hs, false));
    
    TaskGenerateImportApi(m_ctxt, out_h.get(), out_c.get()).generate();

    out_c->close();
    out_h->close();
}

dmgr::IDebug *TaskGenerateModel::m_dbg = 0;

}
}
}
