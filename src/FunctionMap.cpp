/*
 * FunctionMap.cpp
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
#include "FunctionMap.h"


namespace zsp {
namespace be {
namespace sw {


FunctionMap::FunctionMap() {

}

FunctionMap::~FunctionMap() {

}

bool FunctionMap::addFunction(
    arl::dm::IDataTypeFunction      *func,
    FunctionFlags                   flags) {

    if (m_func_m.find(func) == m_func_m.end()) {
        IFunctionInfo *info = new FunctionInfo(func, func->name());
        info->setFlags(flags);

        m_func_m.insert({func, info});
        m_func_l.push_back(IFunctionInfoUP(info));

        return true;
    } else {
        return false;
    }
}

}
}
}
