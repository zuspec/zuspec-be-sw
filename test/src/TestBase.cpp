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
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include "TestBase.h"
#include "dmgr/FactoryExt.h"
#include "vsc/dm/FactoryExt.h"
#include "zsp/arl/dm/FactoryExt.h"
#include "zsp/be/sw/FactoryExt.h"

namespace zsp {
namespace be {
namespace sw {


TestBase::TestBase() {

}

TestBase::~TestBase() {

}

void TestBase::SetUp() {
    char cwd[1024];
    fprintf(stdout, "SetUp %s\n", ::testing::internal::GetArgvs()[0].c_str());

    getcwd(cwd, sizeof(cwd));

    m_rundir = cwd;
    m_rundir += "/rundir";

    ASSERT_TRUE(makedirs(m_rundir));

    ::testing::UnitTest *inst = ::testing::UnitTest::GetInstance();
    m_testdir = m_rundir + "/" + 
        inst->current_test_info()->test_suite_name() + "_" + inst->current_test_info()->name();

    ASSERT_TRUE(makedirs(m_testdir));

    dmgr::IDebugMgr *dmgr = dmgr_getFactory()->getDebugMgr();
    vsc::dm::IFactory *vsc_dm_f = vsc_dm_getFactory();
    vsc_dm_f->init(dmgr);
    arl::dm::IFactory *arl_dm_f = zsp_arl_dm_getFactory();
    arl_dm_f->init(dmgr);

    m_factory = zsp_be_sw_getFactory();
    m_factory->init(dmgr);

    m_ctxt = arl::dm::IContextUP(
        arl_dm_f->mkContext(vsc_dm_f->mkContext())
    );
}

void TestBase::TearDown() {
    fprintf(stdout, "TearDown\n");
    fflush(stdout);

    if (::testing::UnitTest::GetInstance()->current_test_info()->result()->Passed()) {
        // TODO: Clean up run directory
    }

    m_ctxt.reset();
//    m_vsc_ctxt.reset();
}

bool TestBase::isdir(const std::string &path) {
    struct stat sb;

    if (stat(path.c_str(), &sb) != -1) {
        return ((sb.st_mode & S_IFMT) == S_IFDIR);
    }

    return false;
}

bool TestBase::isfile(const std::string &path) {
    struct stat sb;

    if (stat(path.c_str(), &sb) != -1) {
        return ((sb.st_mode & S_IFMT) == S_IFREG);
    }

    return false;
}

bool TestBase::makedirs(const std::string &path) {
    std::string path_s;
    int sl_i = 1;

    while ((sl_i = path.find('/', sl_i)) != -1) {
        path_s = path.substr(0, sl_i);

        if (!isdir(path_s)) {
            if (mkdir(path_s.c_str(), 0700) == -1) {
                fprintf(stdout, "Failed to make directory \"%s\"\n", path_s.c_str());
                return false;
            }
        }
        
        sl_i++;
    }

    if (!isdir(path)) {
        if (mkdir(path.c_str(), 0700) == -1) {
            fprintf(stdout, "Failed to make full directory \"%s\"\n", path.c_str());
            return false;
        }
    }

    return true;
}

std::string TestBase::getTestDirPath(const std::string &path) {
    std::string ret = m_testdir;
    ret += "/";
    ret += path;
    return ret;
}

void TestBase::createFile(
        const std::string          &path,
        const std::string          &content) {
    std::string fullpath = getTestDirPath(path);
    FILE *fp = fopen(fullpath.c_str(), "w");
    ASSERT_TRUE(fp);

    fwrite(content.c_str(), 1, content.size(), fp);
    
    fclose(fp);
}

IOutput *TestBase::openOutput(const std::string &path) {
    std::string fullpath = m_testdir + "/" + path;
    IOutput *ret = m_factory->mkFileOutput(fullpath);

    return ret;
};

}
}
}
