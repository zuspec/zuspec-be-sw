/*
 * Factory.cpp
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
#include <fstream>
#include "Context.h"
#include "Factory.h"
#include "GeneratorFunctionsThreaded.h"
#include "GeneratorMultiCoreEmbCTest.h"
#include "Output.h"
#include "TaskGenerateC.h"
#include "TaskGenerateExecModel.h"
#include "TaskGenerateType.h"
#include "TaskGenerateTypes.h"
#include "TaskInitContextC.h"


namespace zsp {
namespace be {
namespace sw {


Factory::Factory() : m_dmgr(0) {

}

Factory::~Factory() {

}

void Factory::init(dmgr::IDebugMgr *dmgr) {
    m_dmgr = dmgr;
}

IGeneratorFunctions *Factory::mkGeneratorFunctionsThreaded() {
    return new GeneratorFunctionsThreaded();
}

IGeneratorEvalIterator *Factory::mkGeneratorMultiCoreSingleImageEmbCTest(
        const std::vector<arl::dm::IModelFieldExecutor *>  &executors,
        int32_t                                            dflt_exec,
        IOutput                                            *out_h,
        IOutput                                            *out_c) {
    return new GeneratorMultiCoreEmbCTest(
        getDebugMgr(),
        executors,
        dflt_exec,
        out_h,
        out_c);
}

IContext *Factory::mkContext(arl::dm::IContext *ctxt) {
    return new Context(m_dmgr, ctxt);
}

void Factory::generateC(
        IContext                                        *ctxt,
        const std::vector<vsc::dm::IAccept *>           &roots,
        std::ostream                                    *csrc,
        std::ostream                                    *pub_h,
        std::ostream                                    *prv_h) {
    TaskGenerateC(
        ctxt,
        csrc,
        pub_h,
        prv_h).generate(roots);
}

void Factory::generateExecModel(
        arl::dm::IContext                               *ctxt,
        arl::dm::IDataTypeComponent                     *comp_t,
        arl::dm::IDataTypeAction                        *action_t,
        std::ostream                                    *out_c,
        std::ostream                                    *out_h,
        std::ostream                                    *out_h_prv) {
    TaskGenerateExecModel(ctxt).generate(
        comp_t,
        action_t,
        out_c,
        out_h,
        out_h_prv);
}

void Factory::generateType(
        IContext                                        *ctxt,
        vsc::dm::IDataTypeStruct                        *comp_t,
        std::ostream                                    *out_c,
        std::ostream                                    *out_h) {
    TaskGenerateType(ctxt, out_c, out_h).generate(comp_t);
}

void Factory::generateTypes(
        IContext                                        *ctxt,
        vsc::dm::IDataTypeStruct                        *root,
        const std::string                               &outdir) {
    TaskGenerateTypes(ctxt, outdir).generate(root);
}


void Factory::initContextC(arl::dm::IContext *ctxt) {
    TaskInitContextC(m_dmgr).init(ctxt);
}

IOutput *Factory::mkFileOutput(const std::string &path) {
    std::ofstream *out = new std::ofstream();
    out->open(path, std::fstream::out);

    if (out->is_open()) {
        IOutput *ret = new Output(out, true, "");
        return ret;
    } else {
        return 0; 
    }
}

IFactory *Factory::inst() {
    if (!m_inst) {
        m_inst = FactoryUP(new Factory());
    }
    return m_inst.get();
}

FactoryUP Factory::m_inst;

}
}
}

zsp::be::sw::IFactory *zsp_be_sw_getFactory() {
    return zsp::be::sw::Factory::inst();
}

