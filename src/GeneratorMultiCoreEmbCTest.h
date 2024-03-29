/**
 * GeneratorMultiCoreEmbCTest.h
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
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "NameMap.h"
#include "zsp/arl/dm/IModelFieldExecutor.h"
#include "zsp/be/sw/IOutput.h"
#include "zsp/be/sw/IGeneratorEvalIterator.h"

namespace zsp {
namespace be {
namespace sw {



class GeneratorMultiCoreEmbCTest : public virtual IGeneratorEvalIterator {
public:
    GeneratorMultiCoreEmbCTest(
        dmgr::IDebugMgr                                     *dmgr,
        const std::vector<arl::dm::IModelFieldExecutor *>   &executors,
        int32_t                                             dflt_exec,
        IOutput                                             *out_h,
        IOutput                                             *out_c);

    virtual ~GeneratorMultiCoreEmbCTest();

    virtual void generate(
        arl::dm::IModelFieldComponentRoot   *root,
        arl::dm::IModelEvalIterator         *it) override;

private:
    static dmgr::IDebug                                     *m_dbg;
    dmgr::IDebugMgr                                         *m_dmgr;
    NameMap                                                 m_name_m;
    std::string                                             m_entry_name;
    std::vector<arl::dm::IModelFieldExecutor*>              m_executors;
    int32_t                                                 m_dflt_exec;
    IOutput                                                 *m_out_h;
    IOutput                                                 *m_out_c;

};


}
}
}


