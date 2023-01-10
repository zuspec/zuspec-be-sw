/*
 * TaskGenerateFunctionEmbeddedC.cpp
 *
 * Copyright 2022 Matthew Ballance and Contributors
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
#include <map>
#include "TaskGenerateEmbCExpr.h"
#include "TaskGenerateEmbCProcScope.h"
#include "TaskGenerateEmbCVarDecl.h"
#include "TaskGenerateFunctionEmbeddedC.h"

using namespace zsp::arl::dm;

namespace zsp {
namespace be {
namespace sw {


TaskGenerateFunctionEmbeddedC::TaskGenerateFunctionEmbeddedC(
    dmgr::IDebugMgr         *dmgr,
    NameMap                 *name_m) : 
    m_dmgr(dmgr), m_name_m(name_m), m_out(0) {
    m_gen_decl = false;
    m_scope_depth = 0;

}

TaskGenerateFunctionEmbeddedC::~TaskGenerateFunctionEmbeddedC() {


}

void TaskGenerateFunctionEmbeddedC::generate(
    IOutput                         *out_def,
    arl::dm::IDataTypeFunction      *func) {
    m_gen_decl = false;

    m_out = out_def;
    func->accept(m_this);
}

void TaskGenerateFunctionEmbeddedC::visitDataTypeFunction(arl::dm::IDataTypeFunction *t) {
    m_scope_depth = 0;
    m_out->indent();

    m_scope_s.push_back(t);
//    m_scope_s.push_back(t->getBody());

    TaskGenerateEmbCDataType dt_gen(m_out, m_name_m);

    if (t->getReturnType()) {
        dt_gen.generate(t->getReturnType());
        m_out->write(" ");
    } else {
        m_out->write("void ");
    }

    m_out->write("%s(", m_name_m->getName(t).c_str());

    if (t->getParameters().size() > 0) {
        m_out->write("\n");
        m_out->inc_ind();
        m_out->inc_ind();
        for (uint32_t i=0; i<t->getParameters().size(); i++) {
            m_out->indent();
            dt_gen.generate(t->getParameters().at(i)->getDataType());
            m_out->write(" %s", t->getParameters().at(i)->name().c_str());
            if (i+1 < t->getParameters().size()) {
                m_out->write(",\n");
            }
        }
        m_out->dec_ind();
        m_out->dec_ind();
    } else {
        // No parameters. 
        m_out->write("void");
    }

    m_out->write(") {\n");

    m_out->inc_ind();
    t->getBody()->accept(m_this);
    m_out->dec_ind();

    m_out->println("}");

//    m_scope_s.pop_back();
    m_scope_s.pop_back();
}

}
}
}
