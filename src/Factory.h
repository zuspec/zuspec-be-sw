/**
 * Factory.h
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
#include <memory>
#include "zsp/be/sw/FactoryExt.h"

namespace zsp {
namespace be {
namespace sw {


class Factory;
using FactoryUP=std::unique_ptr<Factory>;
class Factory : public virtual IFactory {
public:
    Factory();

    virtual ~Factory();

    virtual void init(dmgr::IDebugMgr *dmgr) override;

    virtual dmgr::IDebugMgr *getDebugMgr() override {
        return m_dmgr;
    }

    virtual IGeneratorFunctions *mkGeneratorFunctionsThreaded() override;

    virtual IGeneratorEvalIterator *mkGeneratorMultiCoreSingleImageEmbCTest(
        const std::vector<arl::dm::IModelFieldExecutor *>  &executors,
        int32_t                                            dflt_exec,
        IOutput                                            *out_h,
        IOutput                                            *out_c) override;

    virtual IContext *mkContext(arl::dm::IContext *ctxt) override;

    virtual void generateC(
        IContext                                        *ctxt,
        const std::vector<vsc::dm::IAccept *>           &roots,
        std::ostream                                    *csrc,
        std::ostream                                    *pub_h,
        std::ostream                                    *prv_h
    ) override;

    virtual void generateExecModel(
        arl::dm::IContext                               *ctxt,
        arl::dm::IDataTypeComponent                     *comp_t,
        arl::dm::IDataTypeAction                        *action_t,
        std::ostream                                    *out_c,
        std::ostream                                    *out_h,
        std::ostream                                    *out_h_prv) override;

    virtual void generateType(
        IContext                                        *ctxt,
        vsc::dm::IDataTypeStruct                        *comp_t,
        std::ostream                                    *out_c,
        std::ostream                                    *out_h) override;

    virtual void generateTypes(
        IContext                                        *ctxt,
        vsc::dm::IDataTypeStruct                        *root,
        const std::string                               &outdir) override;

    virtual void generateModel(
        IContext                                        *ctxt,
        const std::string                               &name,
        arl::dm::IDataTypeComponent                     *pss_top,
        const std::string                               &outdir) override;

    virtual arl::dm::ITypeProcStmtScope *buildAsyncScopeGroup(
        IContext                                        *ctxt,  
        vsc::dm::IAccept                                *scope) override;

    virtual void initContextC(arl::dm::IContext *ctxt) override;

    virtual IOutput *mkFileOutput(const std::string &path) override;

    static IFactory *inst();

private:
    static FactoryUP                m_inst;
    dmgr::IDebugMgr                 *m_dmgr;
};

}
}
}



