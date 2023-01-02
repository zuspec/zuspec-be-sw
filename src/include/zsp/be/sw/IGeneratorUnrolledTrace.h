/**
 * IGeneratorUnrolledTrace.h
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
#include <iostream>
#include <memory>
#include <vector>
#include "zsp/IAccept.h"
#include "zsp/IMarker.h"
#include "zsp/IModelActivity.h"
#include "zsp/IModelFieldComponent.h"

namespace zsp {
namespace be {
namespace sw {


class IGeneratorUnrolledTrace;
using IGeneratorUnrolledTraceUP=std::unique_ptr<IGeneratorUnrolledTrace>;
class IGeneratorUnrolledTrace {
public:

    virtual ~IGeneratorUnrolledTrace() { }

    virtual void generate(
        std::ostream                *c_os,
        std::ostream                *h_os,
        arl::IModelFieldComponent                *pss_top,
//        std::vector // TODO: executors
        const std::vector<IModelActivity *>      &activities,
        std::vector<IMarkerUP>                   &markers
    ) = 0;

};

} /* namespace sw */
} /* namespace be */
} /* namespace arl */


