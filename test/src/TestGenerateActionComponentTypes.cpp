/*
 * TestGenerateActionComponentTypes.cpp
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
#include "TestGenerateActionComponentTypes.h"

using namespace zsp::arl::dm;
using namespace vsc::dm;

namespace zsp {
namespace be {
namespace sw {


TestGenerateActionComponentTypes::TestGenerateActionComponentTypes() {

}

TestGenerateActionComponentTypes::~TestGenerateActionComponentTypes() {

}

TEST_F(TestGenerateActionComponentTypes, smoke) {
    NameMap name_m;
    IOutputUP out_c(openOutput("test.c"));
    IOutputUP out_h(openOutput("test.h"));

    out_c->println("#include <stdio.h>");
    out_c->println("#include \"test.h\"");

    IDataTypeComponentUP pss_top(m_ctxt->mkDataTypeComponent("pss_top"));
    IDataTypeActionUP A_t(m_ctxt->mkDataTypeAction("pss_top::A"));
    A_t->setComponentType(pss_top.get());
    IDataTypeIntUP int32_t(m_ctxt->mkDataTypeInt(true, 32));

    A_t->addField(m_ctxt->mkTypeFieldPhy(
        "v1",
        int32_t.get(),
        false,
        vsc::dm::TypeFieldAttr::Rand,
        0));

    std::vector<vsc::dm::IDataTypeStruct *> types;
    TaskCollectSortTypes collector(m_ctxt->getDebugMgr());
    
    collector.collect(pss_top.get());
    collector.collect(A_t.get());
    collector.sort(types);

    name_m.setName(A_t.get(), "pss_top__A");

    TaskGenerateEmbCStruct struct_gen(out_h.get(), &name_m);

    for (std::vector<vsc::dm::IDataTypeStruct *>::const_iterator
        it=types.begin();
        it!=types.end(); it++) {
        struct_gen.generate(*it);
    }

    out_c->close();
    out_h->close();

}

}
}
}
