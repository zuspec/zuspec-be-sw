/*
 * TestCollectSortCompTreeTypes.cpp
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
#include "TestCollectSortCompTreeTypes.h"
#include "TaskCollectSortTypes.h"

using namespace zsp::arl::dm;


namespace zsp {
namespace be {
namespace sw {


TestCollectSortCompTreeTypes::TestCollectSortCompTreeTypes() {

}

TestCollectSortCompTreeTypes::~TestCollectSortCompTreeTypes() {

}

TEST_F(TestCollectSortCompTreeTypes, smoke) {
    IDataTypeComponentUP pss_top(m_ctxt->mkDataTypeComponent("pss_top"));
    IDataTypeComponentUP c1_t(m_ctxt->mkDataTypeComponent("C1"));
    IDataTypeComponentUP c2_t(m_ctxt->mkDataTypeComponent("C2"));

    fprintf(stdout, "DebugMgr: %p\n", m_ctxt->getDebugMgr());
    m_ctxt->getDebugMgr()->enable(true);
    m_ctxt->getDebugMgr()->enable(true);

    c2_t->addField(m_ctxt->mkTypeFieldPhy(
        "c1_1",
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
}

}
}
}
