/*
 * GeneratorFunctionsThreaded.cpp
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
#include "GeneratorFunctionsThreaded.h"
#include "FunctionMap.h"
#include "TaskCollectReferencedFunctions.h"
#include "TaskGenerateFuncProtoEmbeddedC.h"
#include "TaskGenerateFunctionEmbeddedC.h"


namespace zsp {
namespace be {
namespace sw {


GeneratorFunctionsThreaded::GeneratorFunctionsThreaded() {

}

GeneratorFunctionsThreaded::~GeneratorFunctionsThreaded() {

}

void GeneratorFunctionsThreaded::generate(
        arl::dm::IContext                                   *ctxt,
        const std::vector<arl::dm::IDataTypeFunction *>     &funcs,
        const std::vector<std::string>                      &inc_c,
        const std::vector<std::string>                      &inc_h,
        IOutput                                             *out_c,
        IOutput                                             *out_h) {
    NameMapUP name_m(new NameMap());
    IFunctionMapUP func_m(new FunctionMap());
    TaskCollectReferencedFunctions collector(func_m.get());
    TaskGenerateFuncProtoEmbeddedC proto_gen(name_m.get());
    TaskGenerateFunctionEmbeddedC func_gen(name_m.get());

    // Collect all functions
    // - Root functions provided
    // - All functions called by those functions
    //
    // Mark root functions as Export
    for (std::vector<arl::dm::IDataTypeFunction *>::const_iterator
        it=funcs.begin();
        it!=funcs.end(); it++) {
        // All root functions are export
        func_m->addFunction(
            *it,
            FunctionFlags::Import);

        collector.collect(*it);
    }


    // Add inc_h to out_h
    // Declare Export function prototypes in out_h
    for (std::vector<std::string>::const_iterator
        it=inc_h.begin();
        it!=inc_h.end(); it++) {
        out_h->println("#include \"%s\"", it->c_str());
    }
    for (std::vector<IFunctionInfoUP>::const_iterator
        it=func_m->getFunctions().begin();
        it!=func_m->getFunctions().end(); it++) {
        if (((*it)->getFlags() & FunctionFlags::Export) != FunctionFlags::NoFlags) {
            // Declare export function prototypes
            proto_gen.generate(
                out_h,
                (*it)->getDecl());
        }
    }

    // Add inc_c to out_c
    // Declare non-Export function prototypes in out_c (static?)
    for (std::vector<IFunctionInfoUP>::const_iterator
        it=func_m->getFunctions().begin();
        it!=func_m->getFunctions().end(); it++) {
        if (((*it)->getFlags() & FunctionFlags::Export) == FunctionFlags::NoFlags) {
            // Declare non-export function prototypes
            proto_gen.generate(
                out_h,
                (*it)->getDecl());
        }
    }

    // Implement all functions in out_c
    for (std::vector<IFunctionInfoUP>::const_iterator
        it=func_m->getFunctions().begin();
        it!=func_m->getFunctions().end(); it++) {
        func_gen.generate(
            out_c,
            (*it)->getDecl());
    }
}

}
}
}
