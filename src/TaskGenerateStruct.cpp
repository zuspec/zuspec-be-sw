/*
 * TaskGenerateStruct.cpp
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
#include "GenRefExprExecModel.h"
#include "ITaskGenerateExecModelCustomGen.h"
#include "TaskGatherTypes.h"
#include "TaskGenerateStruct.h"
#include "TaskBuildTypeInfo.h"
#include "TaskGenerateExecBlockNB.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateStruct.h"
#include "TaskGenerateStructDtor.h"
#include "TaskGenerateStructInit.h"
#include "TaskGenerateStructStruct.h"
#include "TaskGenerateStructType.h"

namespace zsp {
namespace be {
namespace sw {

TaskGenerateStruct::TaskGenerateStruct(
    IContext                *ctxt, 
    TypeInfo                *info,   
    IOutput                 *out_h,
    IOutput                 *out_c) : 
    m_dbg(0), m_ctxt(ctxt), m_info(info), m_out_h(out_h), m_out_c(out_c) {
    DEBUG_INIT("zsp::be::sw::TaskGenerateStruct", ctxt->getDebugMgr());
}

TaskGenerateStruct::~TaskGenerateStruct() {

}

void TaskGenerateStruct::generate(vsc::dm::IDataTypeStruct *t) {
    DEBUG_ENTER("generate");

    // Header file is organized as follows
    // 1. Data-type declaration (struct <type>_s)
    // 2. Data-type type declaration (struct <type>__type_s)
    // 3. Type-accessor function (<type>__type())
    // 4. Type-initializer function (<type>__init())

    // C file is organized as follows
    // 1. static dtor function
    // 0..N type methods
    // N+1. get-type function (which depends on dtor)
    // N+2. init function
    m_out_h->println("#ifndef INCLUDED_%s_H", m_ctxt->nameMap()->getName(t).c_str());
    m_out_h->println("#define INCLUDED_%s_H", m_ctxt->nameMap()->getName(t).c_str());
    generate_header_includes(t, m_out_h);
    generate_header_typedefs(t, m_out_h);


    generate_data_type(t, m_out_h);
    generate_source_includes(t, m_out_c);
    generate_dtor(t, m_out_c);
    generate_exec_blocks(t, m_out_c);
    generate_type(t, m_out_h, m_out_c);
    generate_init(t, m_out_h, m_out_c);
    m_out_h->println("#endif /* INCLUDED_%s_H */", m_ctxt->nameMap()->getName(t).c_str());
    DEBUG_LEAVE("generate");
}

void TaskGenerateStruct::generate_data_type(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_type");
    TaskGenerateStructStruct(m_ctxt, m_info, out).generate(t);
    DEBUG_LEAVE("generate_type");
}

void TaskGenerateStruct::generate_header_includes(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_header_includes");
    // TODO: collect all non-handle types
    // Standard includes
    out->println("#include <stdint.h>");
    if (!t->getSuper()) {
        out->println("#include \"zsp/be/sw/rt/%s\"", default_base_header());
    }
    for (std::set<vsc::dm::IDataTypeStruct *>::const_iterator
         it=m_info->referencedValTypes().begin();
         it!=m_info->referencedValTypes().end(); it++) {
        ITaskGenerateExecModelCustomGen *gen = 
            dynamic_cast<ITaskGenerateExecModelCustomGen *>((*it)->getAssociatedData());
        if (gen) {
            gen->genDeclaration(m_ctxt, out, *it, true);
        } else {
            out->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(*it).c_str());
        }
    }
    out->println("#include \"model_api.h\"");

    DEBUG_LEAVE("generate_header_includes");
}

void TaskGenerateStruct::generate_header_typedefs(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_header_typedefs");
    // TODO: collect all handle types
    out->println("struct zsp_actor_s;");

    DEBUG_LEAVE("generate_header_typedefs");
}

void TaskGenerateStruct::generate_source_includes(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_source_includes");
    TaskGatherTypes types(m_ctxt);
    types.gather(t);
    out->println("#include \"zsp/be/sw/rt/zsp_activity_traverse.h\"");
    out->println("#include \"zsp/be/sw/rt/zsp_executor.h\"");
    out->println("#include \"zsp/be/sw/rt/zsp_thread.h\"");
    out->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(t).c_str());
    for (std::vector<vsc::dm::IDataTypeStruct *>::const_iterator
        it=types.types().begin();
        it!=types.types().end(); it++) {
        out->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(*it).c_str());
    }
    // TODO: need to include *our* actor...
    out->println("#include \"zsp/be/sw/rt/zsp_actor.h\"");
    out->println("");

    DEBUG_LEAVE("generate_source_includes");
}

void TaskGenerateStruct::generate_type(
    vsc::dm::IDataTypeStruct    *t,
    IOutput                     *out_h,
    IOutput                     *out_c) {
    DEBUG_ENTER("generate_type");
    TaskGenerateStructType(m_ctxt, m_out_h, m_out_c).generate(t);
    DEBUG_LEAVE("generate_type");
}

void TaskGenerateStruct::generate_init(
    vsc::dm::IDataTypeStruct    *t,
    IOutput                     *out_h,
    IOutput                     *out_c) {
    DEBUG_ENTER("generate_init");
    TaskGenerateStructInit(m_ctxt, m_out_h, m_out_c).generate(t);
    DEBUG_LEAVE("generate_init");
}

void TaskGenerateStruct::generate_dtor(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    TaskGenerateStructDtor(m_ctxt, out).generate(t);
    out->println("");
}

void TaskGenerateStruct::generate_exec_blocks(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_exec_blocks");
    arl::dm::IDataTypeArlStruct *arl_t = dynamic_cast<arl::dm::IDataTypeArlStruct *>(t);

    if (arl_t) {
        std::vector<arl::dm::ExecKindT> kinds = {
            arl::dm::ExecKindT::PreSolve,
            arl::dm::ExecKindT::PostSolve,
            arl::dm::ExecKindT::PreBody
        };
        std::vector<std::string> names = {
            "pre_solve",
            "post_solve",
            "pre_body"
        };

        GenRefExprExecModel refgen(m_ctxt->getDebugMgr(), t, "this_p", true);
        for (auto kind = kinds.begin(); kind != kinds.end(); kind++) {
            const std::vector<arl::dm::ITypeExecUP> &execs = arl_t->getExecs(*kind);
            std::string tname = m_ctxt->nameMap()->getName(t);
            std::string fname = tname + "__" + names[(int)(kind-kinds.begin())];
            TaskGenerateExecBlockNB(m_ctxt, &refgen, m_out_c).generate(
                fname,
                tname,
                execs);
        }
    }
    DEBUG_LEAVE("generate_exec_blocks");
}

}
}
}
