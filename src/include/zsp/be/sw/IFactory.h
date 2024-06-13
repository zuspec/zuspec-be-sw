/**
 * IFactory.h
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
#include "dmgr/IDebugMgr.h"
#include "zsp/arl/dm/IModelFieldExecutor.h"
#include "zsp/be/sw/IContext.h"
#include "zsp/be/sw/IGeneratorEvalIterator.h"
#include "zsp/be/sw/IGeneratorFunctions.h"
#include "zsp/be/sw/IOutput.h"

namespace zsp {
namespace be {
namespace sw {



class IFactory {
public:

    virtual ~IFactory() { }

    virtual void init(dmgr::IDebugMgr *dmgr) = 0;

    virtual dmgr::IDebugMgr *getDebugMgr() = 0;

    virtual IGeneratorFunctions *mkGeneratorFunctionsThreaded() = 0;

    virtual IGeneratorEvalIterator *mkGeneratorMultiCoreSingleImageEmbCTest(
        const std::vector<arl::dm::IModelFieldExecutor *> &executors,
        int32_t                                           dflt_exec,
        IOutput                                           *out_h,
        IOutput                                           *out_c
    ) = 0;

    virtual IContext *mkContext(arl::dm::IContext *ctxt) = 0;

    virtual void generateC(
        IContext                                        *ctxt,
        const std::vector<vsc::dm::IAccept *>           &roots,
        std::ostream                                    *csrc,
        std::ostream                                    *pub_h,
        std::ostream                                    *prv_h
    ) = 0;

    virtual void generateExecModel(
        arl::dm::IContext                               *ctxt,
        arl::dm::IDataTypeComponent                     *comp_t,
        arl::dm::IDataTypeAction                        *action_t,
        std::ostream                                    *out_c,
        std::ostream                                    *out_h,
        std::ostream                                    *out_h_prv) = 0;


    virtual void initContextC(arl::dm::IContext *ctxt) = 0;

    virtual IOutput *mkFileOutput(const std::string &path) = 0;

};

} /* namespace sw */
} /* namespace be */
} /* namespace zsp */


