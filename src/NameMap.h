/**
 * NameMap.h
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
#include <string>
#include <unordered_map>
#include "zsp/arl/dm/IDataTypeFunction.h"
#include "zsp/arl/dm/impl/VisitorBase.h"
#include "vsc/dm/IDataType.h"

namespace zsp {
namespace be {
namespace sw {

class NameMap;
using NameMapUP=std::unique_ptr<NameMap>;
/**
 * @brief Supports name mangling function and type names
 * 
 */
class NameMap : public arl::dm::VisitorBase {
public:
    NameMap();

    virtual ~NameMap();

    void setName(vsc::dm::IDataType *type, const std::string &name);

    void setName(arl::dm::IDataTypeFunction *func, const std::string &name);

    const std::string &getName(vsc::dm::IDataType *type);

    const std::string &getName(arl::dm::IDataTypeFunction *func);

	virtual void visitDataTypeFunction(arl::dm::IDataTypeFunction *t) override;

private:
    std::string                                                     m_name;
    std::unordered_map<vsc::dm::IDataType *,std::string>            m_type_m;
    std::unordered_map<arl::dm::IDataTypeFunction *,std::string>    m_func_m;

};

}
}
}


