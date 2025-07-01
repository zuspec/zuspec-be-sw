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
#include <fstream>
#include "dmgr/impl/DebugMacros.h"
#include "TaskGatherCompTypes.h"
#include "TaskGatherTypes.h"
#include "TaskGenerateModel.h"
#include "TaskGenerateType.h"
#include "TaskGenerateImportApi.h"
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

    FileUtil::mkdirs(m_outdir);

    std::vector<arl::dm::IDataTypeComponent *> comp_types;

    TaskGatherCompTypes(m_ctxt).gather(pss_top, comp_types);

    for (std::vector<arl::dm::IDataTypeComponent *>::const_iterator
        it=comp_types.begin();
        it!=comp_types.end(); it++) {
        std::string basename = m_outdir + "/";
        basename += m_ctxt->nameMap()->getName(*it);

        std::ofstream out_c(basename + ".c");
        std::ofstream out_h(basename + ".h");

        TaskGenerateType(m_ctxt, &out_h, &out_c).generate(*it);
        out_c.close();
        out_h.close();
    }

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

    for (std::vector<vsc::dm::IAccept *>::const_iterator
        it=actions_l.begin();
        it!=actions_l.end(); it++) {
        types.gather(*it);
    }

    // TODO: Generate the import API
    // - Re-iterate core functions for simplicity
    //
    // TODO: Generate library entry-point functions
    // - 

    for (std::vector<vsc::dm::IDataTypeStruct *>::const_iterator
        it=types.types().begin();
        it!=types.types().end(); it++) {
        std::string basename = m_outdir + "/";
        basename += m_ctxt->nameMap()->getName(*it);

        std::ofstream out_c(basename + ".c");
        std::ofstream out_h(basename + ".h");

        TaskGenerateType(m_ctxt, &out_h, &out_c).generate(*it);
        out_c.close();
        out_h.close();
    }

    generate_interface(actions_l);

    generate_api();

    DEBUG_LEAVE("generate");
}

void TaskGenerateModel::generate_interface(
        const std::vector<vsc::dm::IAccept *>   &actors) {
    std::ofstream out_cs(m_outdir + "/model.c");
    std::ofstream out_hs(m_outdir + "/model.h");

    IOutputUP out_c(new Output(&out_cs, false));
    IOutputUP out_h(new Output(&out_hs, false));

    // Generate the interface method prototypes
    out_h->println("#ifndef INCLUDED_MODEL_H");
    out_h->println("#define INCLUDED_MODEL_H");
    out_h->println("#include \"zsp/be/sw/rt/zsp_actor.h\"");
    out_h->println("#include \"model_api.h\"");
    out_h->println("#ifdef __cplusplus");
    out_h->println("extern \"C\" {");
    out_h->println("#endif");
    out_h->println("");
    out_h->println("zsp_actor_type_t **model_get_actor_types();");
    out_h->println("const char **model_get_import_types();");
    out_h->println("");
    out_h->println("#ifdef __cplusplus");
    out_h->println("}");
    out_h->println("#endif");

    out_h->println("#endif /* INCLUDED_MODEL_H */");

    out_c->println("#include \"model.h\"");
    out_c->println("");
    out_c->println("zsp_actor_type_t **model_get_actor_types() {");
    out_c->inc_ind();
    out_c->println("static zsp_actor_type_t *actors[] = {");
    out_c->inc_ind();
    out_c->println("0");
    out_c->dec_ind();
    out_c->println("};");
    out_c->println("return actors;");
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
