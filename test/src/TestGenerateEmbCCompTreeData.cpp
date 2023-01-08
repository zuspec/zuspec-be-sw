/*
 * TestGenerateEmbCCompTreeData.cpp
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
#include "zsp/arl/dm/impl/ModelBuildContext.h"
#include "TaskCollectSortTypes.h"
#include "TaskGenerateEmbCStruct.h"
#include "TaskGenerateEmbCCompTreeData.h"
#include "TestGenerateEmbCCompTreeData.h"

using namespace zsp::arl::dm;
using namespace vsc::dm;

namespace zsp {
namespace be {
namespace sw {


TestGenerateEmbCCompTreeData::TestGenerateEmbCCompTreeData() {

}

TestGenerateEmbCCompTreeData::~TestGenerateEmbCCompTreeData() {

}

TEST_F(TestGenerateEmbCCompTreeData, smoke) {
    NameMap name_m;
    IOutputUP out_c(openOutput("test.c"));
    IOutputUP out_h(openOutput("test.h"));

    out_c->println("#include <stdio.h>");
    out_c->println("#include \"test.h\"");

    IDataTypeComponentUP pss_top(m_ctxt->mkDataTypeComponent("pss_top"));
    IDataTypeComponentUP c1_t(m_ctxt->mkDataTypeComponent("C1"));
    IDataTypeComponentUP c2_t(m_ctxt->mkDataTypeComponent("C2"));
    IDataTypeIntUP int32_t(m_ctxt->mkDataTypeInt(true, 32));

    m_ctxt->getDebugMgr()->enable(true);

    c1_t->addField(m_ctxt->mkTypeFieldPhy(
        "v1",
        int32_t.get(),
        false,
        TypeFieldAttr::NoAttr,
        0));

    c2_t->addField(m_ctxt->mkTypeFieldPhy(
        "c1_1",
        c1_t.get(),
        false,
        vsc::dm::TypeFieldAttr::NoAttr,
        0));
    c2_t->addField(m_ctxt->mkTypeFieldPhy(
        "c1_2",
        c1_t.get(),
        false,
        vsc::dm::TypeFieldAttr::NoAttr,
        0));
    pss_top->addField(m_ctxt->mkTypeFieldPhy(
        "c2_1",
        c2_t.get(),
        false,
        vsc::dm::TypeFieldAttr::NoAttr,
        0));

    fprintf(stdout, "DebugMgr: %p\n", m_ctxt->getDebugMgr());
    std::vector<vsc::dm::IDataTypeStruct *> types;
    TaskCollectSortTypes collector(m_ctxt->getDebugMgr());
    
    collector.collect(pss_top.get());
    collector.sort(types);

    ASSERT_EQ(types.size(), 3);
    ASSERT_EQ(types.at(0)->name(), "C1");
    ASSERT_EQ(types.at(1)->name(), "C2");
    ASSERT_EQ(types.at(2)->name(), "pss_top");

    TaskGenerateEmbCStruct struct_gen(
        m_ctxt->getDebugMgr(), out_h.get(), &name_m);

    for (std::vector<vsc::dm::IDataTypeStruct *>::const_iterator
        it=types.begin();
        it!=types.end(); it++) {
        struct_gen.generate(*it);
    }

    arl::dm::ModelBuildContext build_ctxt(m_ctxt.get());
    arl::dm::IModelFieldComponentRoot *root = 
        pss_top->mkRootFieldT<arl::dm::IModelFieldComponentRoot>(
            &build_ctxt, "pss_top", false);
    ASSERT_TRUE(root);

    // Now, configure the value of c2_1.c1_1.v1 and c2_1.c1_2.v1
    root->fields().at(1)->fields().at(1)->fields().at(1)->val()->set_val_u(1);
    root->fields().at(1)->fields().at(2)->fields().at(1)->val()->set_val_u(2);

    TaskGenerateEmbCCompTreeData(
        m_ctxt->getDebugMgr(),
        out_c.get(), 
        &name_m).generate(root);

    out_c->println("");
    out_c->println("int main() {");
    out_c->inc_ind();

    out_c->println("if (comp_tree.c2_1.c1_1.v1 == 1) {");
    out_c->inc_ind();
    out_c->println("fprintf(stdout, \"PASSED\\n\");");
    out_c->dec_ind();
    out_c->println("} else {");
    out_c->inc_ind();
    out_c->println("fprintf(stdout, \"FAILED\\n\");");
    out_c->dec_ind();
    out_c->println("}");
    
    out_c->println("if (comp_tree.c2_1.c1_2.v1 == 2) {");
    out_c->inc_ind();
    out_c->println("fprintf(stdout, \"PASSED\\n\");");
    out_c->dec_ind();
    out_c->println("} else {");
    out_c->inc_ind();
    out_c->println("fprintf(stdout, \"FAILED\\n\");");
    out_c->dec_ind();
    out_c->println("}");

    out_c->dec_ind();
    out_c->println("}");

    out_c->close();
    out_h->close();

    compileAndRun({
        "test.c",
    });
}

}
}
}
