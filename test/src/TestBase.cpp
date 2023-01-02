/*
 * TestBase.cpp
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
#include "TestBase.h"
#include "dmgr/FactoryExt.h"
#include "vsc/dm/FactoryExt.h"
#include "zsp/arl/dm/FactoryExt.h"

namespace zsp {
namespace be {
namespace sw {


TestBase::TestBase() {

}

TestBase::~TestBase() {

}

void TestBase::SetUp() {
    fprintf(stdout, "SetUp %s\n", ::testing::internal::GetArgvs()[0].c_str());

    ::testing::UnitTest::GetInstance()->current_test_info()->name();
    dmgr::IDebugMgr *dmgr = dmgr_getFactory()->getDebugMgr();
    vsc::dm::IFactory *vsc_dm_f = vsc_dm_getFactory();
    vsc_dm_f->init(dmgr);
    arl::dm::IFactory *arl_dm_f = zsp_arl_dm_getFactory();
    arl_dm_f->init(dmgr);

    m_ctxt = arl::dm::IContextUP(
        arl_dm_f->mkContext(vsc_dm_f->mkContext())
    );
}

void TestBase::TearDown() {
    fprintf(stdout, "TearDown\n");
    fflush(stdout);

    m_ctxt.reset();
//    m_vsc_ctxt.reset();
}

}
}
}
