/*
 * TaskGenerateImportApi.cpp
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
#include "TaskGenerateImportApi.h"


namespace zsp {
namespace be {
namespace sw {


TaskGenerateImportApi::TaskGenerateImportApi(
    IContext                        *ctxt,
    IOutput                         *out_h,
    IOutput                         *out_c) : m_ctxt(ctxt), m_out_h(out_h), m_out_c(out_c) {

}

TaskGenerateImportApi::~TaskGenerateImportApi() {

}

void TaskGenerateImportApi::generate() {

    m_out_h->println("#ifndef INCLUDED_MODEL_API_H");
    m_out_h->println("#define INCLUDED_MODEL_API_H");
    m_out_h->println("#include <stdint.h>");
    m_out_h->println("#include <stdarg.h>");
    m_out_h->println("");
    m_out_h->println("struct zsp_api_s;");
    m_out_h->println("struct zsp_frame_s;");
    m_out_h->println("struct zsp_thread_s;");
    m_out_h->println("");
    m_out_h->println("typedef struct model_api_s {");
    m_out_h->inc_ind();
    // First, add known interface functions
    m_out_h->println("void (*print)(struct zsp_api_s *api, const char *msg);");
    m_out_h->println("void (*message)(struct zsp_api_s *api, const char *msg);");
    for (std::vector<arl::dm::IDataTypeFunction *>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeFunctions().begin();
        it != m_ctxt->ctxt()->getDataTypeFunctions().end(); it++) {
        arl::dm::IDataTypeFunction *f = *it;
        if (f->getImportSpecs().size() == 0 
            || f->hasFlags(arl::dm::DataTypeFunctionFlags::Core)
            || !f->hasFlags(arl::dm::DataTypeFunctionFlags::Import)) {
            // Ignore non-import functions
            continue;
        }

        m_out_h->indent();
        if (f->hasFlags(arl::dm::DataTypeFunctionFlags::Target)) {
            m_out_h->write("struct zsp_frame_s *(*%s)(struct zsp_thread_s *, int32_t, va_list *);\n", 
                f->name().c_str());
        } else {
            if (f->getReturnType()) {
                m_ptype.clear();
                f->getReturnType()->accept(this);
                m_out_h->write("%s ", m_ptype.c_str());
            } else {
                m_out_h->write("void ");
            }
            m_out_h->write("(*%s)(struct zsp_api_s *api", f->name().c_str());

            for (std::vector<arl::dm::IDataTypeFunctionParamDecl *>::const_iterator
                pit=f->getParameters().begin();
                pit != f->getParameters().end(); pit++) {
                m_out_h->write(", ");
                m_ptype.clear();
                (*pit)->getDataType()->accept(this);
                m_out_h->write("%s %s", m_ptype.c_str(), (*pit)->name().c_str());
            }
            m_out_h->write(");\n");
        }
    }
    m_out_h->dec_ind();
    m_out_h->println("} model_api_t;");

    m_out_c->println("#include \"model_api.h\"");
    m_out_c->println("#include \"model.h\"");
    m_out_c->println("");
    m_out_c->println("const char **model_get_import_types() {");
    m_out_c->inc_ind();
    m_out_c->println("static const char *imports[] = {");
    m_out_c->inc_ind();
    bool have = false;
    for (std::vector<arl::dm::IDataTypeFunction *>::const_iterator
        it=m_ctxt->ctxt()->getDataTypeFunctions().begin();
        it != m_ctxt->ctxt()->getDataTypeFunctions().end(); it++) {
        arl::dm::IDataTypeFunction *f = *it;
        if (f->getImportSpecs().size() == 0 
            || f->hasFlags(arl::dm::DataTypeFunctionFlags::Core)
            || !f->hasFlags(arl::dm::DataTypeFunctionFlags::Import)) {
            // Ignore non-import functions
            continue;
        }
        if (have) {
            m_out_c->write(",\n");
        }
        m_out_c->indent();
        char tmp[1024];

        snprintf(tmp, sizeof(tmp), "%d%s", 
            f->name().size(),
            f->name().c_str());
        
        if (f->hasFlags(arl::dm::DataTypeFunctionFlags::Target)) {
            strcat(tmp, "T");
        }

        if (f->getReturnType()) {
            m_type_sig.clear();
            f->getReturnType()->accept(this);
            strcat(tmp, m_type_sig.c_str());
        } else {
            strcat(tmp, "V");
        }

        m_type_sig.clear();
        for (std::vector<arl::dm::IDataTypeFunctionParamDecl *>::const_iterator
            pit=f->getParameters().begin();
            pit != f->getParameters().end(); pit++) {
            (*pit)->getDataType()->accept(this);
        }
        strcat(tmp, m_type_sig.c_str());

        m_out_c->write("\"%s\"", tmp);
        have = true;
    }
    if (have) {
        m_out_c->write(",\n");
    }
    m_out_c->println("0");
    m_out_c->dec_ind();
    m_out_c->println("};");
    m_out_c->dec_ind();
    m_out_c->println("}");

    m_out_h->println("");
    m_out_h->println("#endif /* INCLUDED_MODEL_API_H */");
}

void TaskGenerateImportApi::visitDataTypeInt(vsc::dm::IDataTypeInt *t) {
    if (t->width() <= 8) {
        m_type_sig += t->is_signed()?"c":"C";
        m_ptype += t->is_signed()?"int8_t":"uint8_t";
    } else if (t->width() <= 16) {
        m_type_sig += t->is_signed()?"h":"H";
        m_ptype += t->is_signed()?"int16_t":"uint16_t";
    } else if (t->width() <= 32) {
        m_type_sig += t->is_signed()?"i":"I";
        m_ptype += t->is_signed()?"int32_t":"uint32_t";
    } else {
        m_type_sig += t->is_signed()?"l":"L";
        m_ptype += t->is_signed()?"int64_t":"uint64_t";
    }
}

void TaskGenerateImportApi::visitDataTypeString(vsc::dm::IDataTypeString *t) {
    m_type_sig += "s";
    m_ptype += "const char *";
}

void TaskGenerateImportApi::visitDataTypeStruct(vsc::dm::IDataTypeStruct *t) {
    char tmp[1024];
    snprintf(tmp, sizeof(tmp), "S%d%s", t->name().size(), t->name().c_str());
    m_type_sig += tmp;
//    m_ptype += "const char *";
}

}
}
}
