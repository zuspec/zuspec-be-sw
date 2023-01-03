/**
 * FunctionMap.h
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
#include <map>
#include <vector>
#include "zsp/be/sw/IFunctionMap.h"
#include "FunctionInfo.h"

namespace zsp {
namespace be {
namespace sw {



class FunctionMap : public virtual IFunctionMap {
public:
    FunctionMap();

    virtual ~FunctionMap();

    virtual bool addFunction(
        arl::dm::IDataTypeFunction      *func,
        FunctionFlags                   flags) override;

    virtual const std::vector<IFunctionInfoUP> &getFunctions() const override {
        return m_func_l;
    }

private:
    std::map<arl::dm::IDataTypeFunction *, IFunctionInfo *>     m_func_m;
    std::vector<IFunctionInfoUP>                                m_func_l;

};

}
}
}


