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
#include <spawn.h>
#include <unistd.h>
#include <fcntl.h>
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

void TestBase::compileAndRun(const std::vector<std::string> &args) {
    char tmp[1024];
    std::vector<std::string> output;
    compile(args);
    run(output);



    uint32_t n_pass = 0;
    uint32_t n_fail = 0;
    for (std::vector<std::string>::const_iterator
        it=output.begin();
        it!=output.end(); it++) {
        if (it->find("PASSED") != -1) {
            n_pass++;
        } else if (it->find("FAILED") != -1) {
            n_fail++;
        }
    }

    ASSERT_GT(n_pass, 0);
    ASSERT_EQ(n_fail, 0);
}

void TestBase::compile(const std::vector<std::string> &args) {
    char cwd[1024];

    getcwd(cwd, sizeof(cwd));

    char tmp[1024];
    size_t sz = readlink("/proc/self/exe", tmp, sizeof(tmp));
    tmp[sz] = 0;
    if (sz == -1) {
        fprintf(stdout, "Error: readlink failed\n");
    } else {
        fprintf(stdout, "Success: %s\n", tmp);
    }
    std::string path = tmp;
    path = path.substr(0, path.rfind("/"));
    path = path.substr(0, path.rfind("/"));
    path = path.substr(0, path.rfind("/"));
    path = path + "/test/src/host_backend";
    path = "-I" + path;
    fprintf(stdout, "Dir: %s\n", path.c_str());

    const char **argv = new const char *[args.size()+5+1];
    argv[0] = "gcc";
    argv[1] = "-o";
    argv[2] = "test.exe";
    argv[3] = "-I.";
    argv[4] = strdup(path.c_str());

    for (uint32_t i=0; i<args.size(); i++) {
        argv[5+i] = strdup(args.at(i).c_str());
    }

    argv[args.size()+5] = 0;

    posix_spawn_file_actions_t action;
    std::string outfile = m_testdir + "/compile.out";

    posix_spawn_file_actions_init(&action);
    posix_spawn_file_actions_addopen(&action, STDOUT_FILENO, outfile.c_str(),
            O_WRONLY|O_CREAT|O_TRUNC, 0644);
    posix_spawn_file_actions_adddup2(&action, STDOUT_FILENO, STDERR_FILENO);

    pid_t pid;
    chdir(m_testdir.c_str());
    int status = posix_spawnp(&pid, argv[0], &action, 0, (char *const *)argv, environ);

    ASSERT_EQ(status, 0);
    ASSERT_NE(waitpid(pid, &status, 0), -1);
    chdir(cwd);
    ASSERT_EQ(status, 0);

    for (uint32_t i=0; i<args.size(); i++) {
        free((void *)argv[4+i]);
    }
}

void TestBase::run(std::vector<std::string> &output) {
    char cwd[1024];

    ASSERT_TRUE(getcwd(cwd, sizeof(cwd)));

    const char *argv[] = {
        "./test.exe",
        0
    };

    posix_spawn_file_actions_t action;
    std::string outfile = m_testdir + "/test.out";

    posix_spawn_file_actions_init(&action);
    posix_spawn_file_actions_addopen(&action, STDOUT_FILENO, outfile.c_str(),
            O_WRONLY|O_CREAT|O_TRUNC, 0644);
    posix_spawn_file_actions_adddup2(&action, STDOUT_FILENO, STDERR_FILENO);

    pid_t pid;
    ASSERT_FALSE(chdir(m_testdir.c_str()));
    int status = posix_spawnp(&pid, argv[0], &action, 0, (char *const *)argv, environ);

    ASSERT_EQ(status, 0);
    ASSERT_NE(waitpid(pid, &status, 0), -1);
    ASSERT_FALSE(chdir(cwd));
    ASSERT_EQ(status, 0);

    FILE *fp = fopen(outfile.c_str(), "r");
    ASSERT_TRUE(fp);
    while (!feof(fp)) {
        ASSERT_TRUE(fgets(cwd, sizeof(cwd), fp));
        output.push_back(cwd);
    }
    fclose(fp);
}

}
}
}
