/**
 * TestBase.h
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
#pragma once
#include <string>
#include "gtest/gtest.h"
#include "zsp/arl/dm/IContext.h"
#include "zsp/be/sw/IFactory.h"
#include "vsc/dm/IContext.h"

namespace zsp {
namespace be {
namespace sw {


class TestBase : public ::testing::Test {
public:
    TestBase();

    virtual ~TestBase();

    virtual void SetUp() override;

    virtual void TearDown() override;

protected:
    bool isdir(const std::string &path);

    bool isfile(const std::string &path);

    bool makedirs(const std::string &path);

    // Compute a test-directory relative path
    std::string getTestDirPath(const std::string &path);

    void createFile(
        const std::string          &path,
        const std::string          &content);

    IOutput *openOutput(const std::string &path);

protected:
    arl::dm::IContextUP             m_ctxt;
    IFactory                        *m_factory;
    std::string                     m_rundir;
    std::string                     m_testdir;

};

}
}
}


