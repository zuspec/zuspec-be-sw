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
    IOutput                 *out_h,
    IOutput                 *out_c) : 
    m_dbg(0), m_ctxt(ctxt), m_out_h(out_h), m_out_c(out_c) {
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
    generate_type(t, m_out_h, m_out_c);
    generate_init(t, m_out_h, m_out_c);
    m_out_h->println("#endif /* INCLUDED_%s_H */", m_ctxt->nameMap()->getName(t).c_str());
    DEBUG_LEAVE("generate");
}

void TaskGenerateStruct::generate_data_type(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_type");
    TaskGenerateStructStruct(m_ctxt, out).generate(t);
    DEBUG_LEAVE("generate_type");
}

void TaskGenerateStruct::generate_header_includes(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_header_includes");
    // TODO: collect all non-handle types
    // Standard includes
    out->println("#include <stdint.h>");
    if (t->getSuper()) {
        out->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(t->getSuper()).c_str());
    } else {
        out->println("#include \"zsp/rt/zsp_object.h\"");
    }

    DEBUG_LEAVE("generate_header_includes");
}

void TaskGenerateStruct::generate_header_typedefs(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_header_typedefs");
    // TODO: collect all handle types

    DEBUG_LEAVE("generate_header_typedefs");
}

void TaskGenerateStruct::generate_source_includes(vsc::dm::IDataTypeStruct *t, IOutput *out) {
    DEBUG_ENTER("generate_source_includes");
    out->println("#include \"%s.h\"", m_ctxt->nameMap()->getName(t).c_str());
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

}
}
}
